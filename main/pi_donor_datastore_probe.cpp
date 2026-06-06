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

        contracts.donor_primary_filesystem().remove("/identity/_main.id");

        mesh::LocalIdentity saved_identity;
        mesh::LocalIdentity loaded_identity;

        state_.identity_missing_before_save = !datastore_->loadMainIdentity(loaded_identity);
        state_.identity_saved = datastore_->saveMainIdentity(saved_identity);
        state_.identity_file_ready = contracts.donor_primary_filesystem().exists("/identity/_main.id");
        state_.identity_loaded_after_save = datastore_->loadMainIdentity(loaded_identity);
    }

    state_.probe_ready = state_.datastore_host_ready
        && state_.datastore_constructed
        && state_.begin_called
        && state_.blob_store_ready
        && state_.identity_missing_before_save
        && state_.identity_saved
        && state_.identity_file_ready
        && state_.identity_loaded_after_save;
    return state_;
}

const DonorDataStoreProbeState& PiDonorDataStoreProbe::state() const {
    return state_;
}

DataStore* PiDonorDataStoreProbe::datastore() {
    return datastore_.get();
}

} // namespace pi_port