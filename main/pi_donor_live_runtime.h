#pragma once

#include <memory>

#include "../examples/companion_radio/DataStore.h"
#include "../examples/companion_radio/MyMesh.h"
#include "pi_donor_host_contracts.h"
#include "pi_donor_runtime_bridge.h"

namespace pi_port {

struct DonorLiveRuntimeState {
    bool datastore_constructed;
    bool datastore_begun;
    bool radio_ready;
    bool rng_seeded;
    bool mesh_constructed;
    bool mesh_begun;
    bool interface_started;
    bool runtime_ready;
};

class PiDonorLiveRuntime {
public:
    PiDonorLiveRuntime();

    const DonorLiveRuntimeState& start(PiDonorRuntimeBridge& bridge, PiDonorHostContracts& contracts);
    void loop_once();
    const DonorLiveRuntimeState& state() const;
    MyMesh* mesh();

private:
    DonorLiveRuntimeState state_;
    StdRNG rng_;
    SimpleMeshTables tables_;
    std::unique_ptr<DataStore> datastore_;
    std::unique_ptr<MyMesh> mesh_;
};

} // namespace pi_port