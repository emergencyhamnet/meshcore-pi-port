#include "pi_runtime_adapter.h"

namespace pi_port {

PiRuntimeAdapter::PiRuntimeAdapter()
    : state_{}, transport_() {}

const RuntimeAdapterState& PiRuntimeAdapter::start() {
    state_ = {};
    state_.boot = boot_runtime_state();

    if (!state_.boot.transport_ready) {
        return state_;
    }

    state_.transport_started = transport_.begin(state_.boot.transport_endpoint);
    if (!state_.transport_started) {
        return state_;
    }

    transport_.enable();
    state_.transport_enabled = transport_.is_enabled() && transport_.is_connected();
    return state_;
}

const RuntimeAdapterState& PiRuntimeAdapter::state() const {
    return state_;
}

PiTransportInterface& PiRuntimeAdapter::transport() {
    return transport_;
}

const PiTransportInterface& PiRuntimeAdapter::transport() const {
    return transport_;
}

} // namespace pi_port