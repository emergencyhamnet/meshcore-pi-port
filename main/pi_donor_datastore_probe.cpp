#include "pi_donor_datastore_probe.h"

namespace pi_port {

bool PiDonorDataStoreHost::onContactLoaded(const ContactInfo&) {
    return true;
}

bool PiDonorDataStoreHost::getContactForSave(uint32_t, ContactInfo&) {
    return false;
}

bool PiDonorDataStoreHost::onChannelLoaded(uint8_t, const ChannelDetails&) {
    return true;
}

bool PiDonorDataStoreHost::getChannelForSave(uint8_t, ChannelDetails&) {
    return false;
}

PiDonorDataStoreProbe::PiDonorDataStoreProbe()
    : state_{}, host_(), datastore_() {}

const DonorDataStoreProbeState& PiDonorDataStoreProbe::bind(PiDonorHostContracts& contracts) {
    state_ = {};
    datastore_.reset();

    state_.datastore_host_ready = true;

    auto* secondary_fs = contracts.donor_secondary_filesystem();
    if (secondary_fs != nullptr) {
        datastore_ = std::make_unique<DataStore>(
            contracts.donor_primary_filesystem(),
            *secondary_fs,
            contracts.donor_rtc_clock());
        state_.using_secondary_filesystem = true;
    } else {
        datastore_ = std::make_unique<DataStore>(
            contracts.donor_primary_filesystem(),
            contracts.donor_rtc_clock());
    }

    state_.datastore_constructed = datastore_ != nullptr;
    if (state_.datastore_constructed) {
        datastore_->begin();
        state_.begin_called = true;
        state_.blob_store_ready = contracts.donor_primary_filesystem().exists("/bl");
    }

    state_.probe_ready = state_.datastore_host_ready
        && state_.datastore_constructed
        && state_.begin_called
        && state_.blob_store_ready;
    return state_;
}

const DonorDataStoreProbeState& PiDonorDataStoreProbe::state() const {
    return state_;
}

DataStore* PiDonorDataStoreProbe::datastore() {
    return datastore_.get();
}

} // namespace pi_port