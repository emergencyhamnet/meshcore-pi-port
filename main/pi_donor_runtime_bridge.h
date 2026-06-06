#pragma once

#include "pi_runtime_adapter.h"

namespace pi_port {

struct DonorRuntimeBridgeState {
    RuntimeAdapterState adapter;
    bool bridge_ready;
    bool donor_runtime_bound;
};

class PiDonorRuntimeBridge {
public:
    PiDonorRuntimeBridge();

    const DonorRuntimeBridgeState& start();
    const DonorRuntimeBridgeState& state() const;
    PiRuntimeAdapter& adapter();
    const PiRuntimeAdapter& adapter() const;

private:
    DonorRuntimeBridgeState state_;
    PiRuntimeAdapter adapter_;
};

} // namespace pi_port