#pragma once

#include "pi_runtime_boot.h"
#include "../platform/pi_transport.h"

namespace pi_port {

struct RuntimeAdapterState {
    RuntimeBootState boot;
    bool transport_started;
    bool transport_enabled;
};

class PiRuntimeAdapter {
public:
    PiRuntimeAdapter();

    const RuntimeAdapterState& start();
    const RuntimeAdapterState& state() const;
    PiTransportInterface& transport();
    const PiTransportInterface& transport() const;

private:
    RuntimeAdapterState state_;
    PiTransportInterface transport_;
};

} // namespace pi_port