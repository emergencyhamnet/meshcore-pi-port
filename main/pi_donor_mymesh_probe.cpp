#include "pi_donor_mymesh_probe.h"

#include <cstring>

namespace {

PiProbeBoard g_probe_board;
PiProbeRadioDriver g_probe_radio_driver;
SensorManager g_probe_sensors;
unsigned long g_probe_millis = 0;

} // namespace

PiProbeBoard board = g_probe_board;
PiProbeRadioDriver radio_driver = g_probe_radio_driver;
SensorManager sensors = g_probe_sensors;

mesh::LocalIdentity radio_new_identity() {
    return mesh::LocalIdentity();
}

unsigned long millis() {
    return g_probe_millis++;
}

void randomSeed(long) {}

long random(long min_value, long) {
    return min_value;
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
        mesh_->begin(false);
        state_.begin_called = true;
        state_.node_name_loaded = std::strcmp(mesh_->getNodeName(), "pi-port-probe") == 0;
        state_.prefs_loaded = mesh_->getNodePrefs() != nullptr
            && std::strcmp(mesh_->getNodePrefs()->node_name, "pi-port-probe") == 0
            && mesh_->getNodePrefs()->freq == 915.5f;

        mesh_->startInterface(contracts.donor_serial_interface());
        state_.interface_started = true;
        state_.serial_enabled_after_start = contracts.serial_host().is_enabled();
        state_.prefs_pointer_ready = mesh_->getNodePrefs() != nullptr;
    }

    state_.probe_ready = state_.mesh_constructed
        && state_.begin_called
        && state_.node_name_loaded
        && state_.prefs_loaded
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