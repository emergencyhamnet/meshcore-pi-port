#include "pi_donor_runtime_bridge.h"
#include "pi_donor_host_contracts.h"
#include "pi_donor_datastore_probe.h"
#include "pi_donor_mymesh_probe.h"

int main() {
    pi_port::PiDonorRuntimeBridge bridge;
    const auto& state = bridge.start();
    pi_port::PiDonorHostContracts contracts;
    const auto& contract_state = contracts.bind(bridge);
    pi_port::PiDonorDataStoreProbe datastore_probe;
    const auto& datastore_state = datastore_probe.bind(contracts);
    pi_port::PiDonorMyMeshProbe mymesh_probe;
    const auto& mymesh_state = mymesh_probe.bind(contracts, datastore_probe);

    if (!state.adapter.boot.board_ready) {
        return 1;
    }

    if (!state.adapter.boot.gpio_ready) {
        return 2;
    }

    if (!state.adapter.boot.spi_ready) {
        return 3;
    }

    if (!state.adapter.boot.radio_path_ready) {
        return 4;
    }

    if (!state.adapter.boot.storage_ready) {
        return 5;
    }

    if (!state.adapter.boot.transport_ready) {
        return 6;
    }

    if (!state.adapter.transport_started) {
        return 7;
    }

    if (!state.adapter.transport_enabled) {
        return 8;
    }

    if (!state.bridge_ready) {
        return 9;
    }

    if (!contract_state.contracts_ready) {
        return 10;
    }

    if (!datastore_state.probe_ready) {
        return 11;
    }

    if (!mymesh_state.probe_ready) {
        return 12;
    }

    return 0;
}