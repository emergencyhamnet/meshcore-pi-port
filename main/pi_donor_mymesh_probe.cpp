#include "pi_donor_mymesh_probe.h"

namespace {

PiProbeBoard g_probe_board;
PiProbeRadioDriver g_probe_radio_driver;
SensorManager g_probe_sensors;

} // namespace

PiProbeBoard board = g_probe_board;
PiProbeRadioDriver radio_driver = g_probe_radio_driver;
SensorManager sensors = g_probe_sensors;

mesh::LocalIdentity radio_new_identity() {
    return mesh::LocalIdentity();
}

namespace pi_port {

int PiDonorMyMeshProbe::ProbeRadio::recvRaw(uint8_t*, int) {
    return 0;
}

uint32_t PiDonorMyMeshProbe::ProbeRadio::getEstAirtimeFor(int) {
    return 0;
}

float PiDonorMyMeshProbe::ProbeRadio::packetScore(float, int) {
    return 0.0f;
}

bool PiDonorMyMeshProbe::ProbeRadio::startSendRaw(const uint8_t*, int) {
    return false;
}

bool PiDonorMyMeshProbe::ProbeRadio::isSendComplete() {
    return true;
}

void PiDonorMyMeshProbe::ProbeRadio::onSendFinished() {}

bool PiDonorMyMeshProbe::ProbeRadio::isInRecvMode() const {
    return true;
}

PiDonorMyMeshProbe::PiDonorMyMeshProbe()
    : radio_(),
      rng_(),
      tables_(),
      state_{},
      mesh_() {}

const DonorMyMeshProbeState& PiDonorMyMeshProbe::bind(PiDonorHostContracts& contracts, PiDonorDataStoreProbe& datastore_probe) {
    state_ = {};
    mesh_.reset();

    auto* store = datastore_probe.datastore();
    if (store == nullptr) {
        return state_;
    }

    mesh_ = std::make_unique<MyMesh>(radio_, rng_, contracts.donor_rtc_clock(), tables_, *store, nullptr);
    state_.mesh_constructed = mesh_ != nullptr;

    if (state_.mesh_constructed) {
        mesh_->startInterface(contracts.donor_serial_interface());
        state_.interface_started = true;
        state_.serial_enabled_after_start = contracts.serial_host().is_enabled();
        state_.prefs_pointer_ready = mesh_->getNodePrefs() != nullptr;
    }

    state_.probe_ready = state_.mesh_constructed
        && state_.interface_started
        && state_.serial_enabled_after_start
        && state_.prefs_pointer_ready;
    return state_;
}

const DonorMyMeshProbeState& PiDonorMyMeshProbe::state() const {
    return state_;
}

MyMesh* PiDonorMyMeshProbe::mesh() {
    return mesh_.get();
}

} // namespace pi_port