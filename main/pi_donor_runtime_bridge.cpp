#include "pi_donor_runtime_bridge.h"

#include <string>

#include "../platform/pi_storage.h"

namespace pi_port {

namespace {

std::string build_runtime_status_text(const DonorRuntimeBridgeState& state) {
    std::string content;
    content += std::string("bridge_ready=") + (state.bridge_ready ? "1" : "0") + "\n";
    content += std::string("donor_runtime_bound=") + (state.donor_runtime_bound ? "1" : "0") + "\n";
    content += std::string("transport_started=") + (state.adapter.transport_started ? "1" : "0") + "\n";
    content += std::string("transport_enabled=") + (state.adapter.transport_enabled ? "1" : "0") + "\n";
    content += std::string("runtime_endpoint=") + state.adapter.boot.runtime_endpoint + "\n";
    return content;
}

} // namespace

PiDonorRuntimeBridge::PiDonorRuntimeBridge()
    : state_{}, adapter_() {}

const DonorRuntimeBridgeState& PiDonorRuntimeBridge::start() {
    state_ = {};
    state_.adapter = adapter_.start();
    state_.bridge_ready = state_.adapter.transport_enabled;
    state_.donor_runtime_bound = false;

    if (state_.adapter.boot.storage_ready) {
        state_.runtime_status_persisted = storage_write_text_file(
            storage_runtime_status_path(state_.adapter.boot.storage),
            build_runtime_status_text(state_));
    }

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