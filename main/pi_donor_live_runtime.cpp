#include "pi_donor_live_runtime.h"

#include "../target.h"

namespace pi_port {

PiDonorLiveRuntime::PiDonorLiveRuntime()
    : state_{},
      rng_{},
      tables_{},
      datastore_{},
      mesh_{} {}

const DonorLiveRuntimeState& PiDonorLiveRuntime::start(PiDonorRuntimeBridge&, PiDonorHostContracts& contracts) {
    state_ = {};
    datastore_.reset();
    mesh_.reset();

    auto* secondary_fs = contracts.donor_secondary_filesystem();
    if (secondary_fs != nullptr) {
        datastore_ = std::make_unique<DataStore>(
            contracts.donor_primary_filesystem(),
            *secondary_fs,
            contracts.donor_rtc_clock());
    } else {
        datastore_ = std::make_unique<DataStore>(
            contracts.donor_primary_filesystem(),
            contracts.donor_rtc_clock());
    }

    state_.datastore_constructed = datastore_ != nullptr;
    if (!state_.datastore_constructed) {
        return state_;
    }

    datastore_->begin();
    state_.datastore_begun = true;

    state_.radio_ready = radio_init();
    if (!state_.radio_ready) {
        return state_;
    }

    rng_.begin(radio_driver.getRngSeed());
    state_.rng_seeded = true;

    mesh_ = std::make_unique<MyMesh>(
        radio_driver,
        rng_,
        contracts.donor_rtc_clock(),
        tables_,
        *datastore_,
        nullptr);
    state_.mesh_constructed = mesh_ != nullptr;
    if (!state_.mesh_constructed) {
        return state_;
    }

    mesh_->begin(false);
    state_.mesh_begun = true;

    mesh_->startInterface(contracts.donor_serial_interface());
    state_.interface_started = true;
    state_.runtime_ready = true;
    return state_;
}

void PiDonorLiveRuntime::loop_once() {
    if (mesh_ == nullptr) {
        return;
    }

    mesh_->loop();
    radio_driver.loop();
    sensors.loop();
}

const DonorLiveRuntimeState& PiDonorLiveRuntime::state() const {
    return state_;
}

MyMesh* PiDonorLiveRuntime::mesh() {
    return mesh_.get();
}

} // namespace pi_port