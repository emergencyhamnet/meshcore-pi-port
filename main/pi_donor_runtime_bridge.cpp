#include "pi_donor_runtime_bridge.h"

namespace pi_port {

PiDonorRuntimeBridge::PiDonorRuntimeBridge()
    : state_{}, adapter_() {}

const DonorRuntimeBridgeState& PiDonorRuntimeBridge::start() {
    state_ = {};
    state_.adapter = adapter_.start();
    state_.bridge_ready = state_.adapter.transport_enabled;
    state_.donor_runtime_bound = false;
    return state_;
}

const DonorRuntimeBridgeState& PiDonorRuntimeBridge::state() const {
    return state_;
}

PiRuntimeAdapter& PiDonorRuntimeBridge::adapter() {
    return adapter_;
}

const PiRuntimeAdapter& PiDonorRuntimeBridge::adapter() const {
    return adapter_;
}

} // namespace pi_port