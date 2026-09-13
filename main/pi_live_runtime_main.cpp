#include "pi_donor_host_contracts.h"
#include "pi_donor_live_runtime.h"
#include "pi_donor_runtime_bridge.h"

#include <string>

#include "../Arduino.h"
#include "../platform/pi_storage.h"

namespace {

std::string bool_line(const char* key, bool value) {
    return std::string(key) + "=" + (value ? "1" : "0") + "\n";
}

void write_runtime_status(
    const pi_port::DonorRuntimeBridgeState& bridge_state,
    const pi_port::DonorHostContractsState& contract_state,
    const pi_port::DonorLiveRuntimeState& runtime_state) {
    if (!bridge_state.adapter.boot.storage_ready) {
        return;
    }

    std::string content;
    content += bool_line("bridge_ready", bridge_state.bridge_ready);
    content += bool_line("donor_runtime_bound", bridge_state.donor_runtime_bound);
    content += bool_line("transport_started", bridge_state.adapter.transport_started);
    content += bool_line("transport_enabled", bridge_state.adapter.transport_enabled);
    content += std::string("runtime_endpoint=") + bridge_state.adapter.boot.runtime_endpoint + "\n";
    content += bool_line("contracts_ready", contract_state.contracts_ready);
    content += bool_line("live_datastore_constructed", runtime_state.datastore_constructed);
    content += bool_line("live_datastore_begun", runtime_state.datastore_begun);
    content += bool_line("live_radio_ready", runtime_state.radio_ready);
    content += bool_line("live_rng_seeded", runtime_state.rng_seeded);
    content += bool_line("live_mesh_constructed", runtime_state.mesh_constructed);
    content += bool_line("live_mesh_begun", runtime_state.mesh_begun);
    content += bool_line("live_interface_started", runtime_state.interface_started);
    content += bool_line("live_runtime_ready", runtime_state.runtime_ready);

    pi_port::storage_write_text_file(
        pi_port::storage_runtime_status_path(bridge_state.adapter.boot.storage),
        content);
}

} // namespace

int main() {
    pi_port::PiDonorRuntimeBridge bridge;
    const auto& bridge_state = bridge.start();

    if (!bridge_state.adapter.boot.board_ready) {
        return 1;
    }
    if (!bridge_state.adapter.boot.gpio_ready) {
        return 2;
    }
    if (!bridge_state.adapter.boot.spi_ready) {
        return 3;
    }
    if (!bridge_state.adapter.boot.radio_path_ready) {
        return 4;
    }
    if (!bridge_state.adapter.boot.storage_ready) {
        return 5;
    }
    if (!bridge_state.adapter.boot.transport_ready) {
        return 6;
    }
    if (!bridge_state.adapter.transport_started) {
        return 7;
    }
    if (!bridge_state.adapter.transport_enabled) {
        return 8;
    }
    if (!bridge_state.bridge_ready) {
        return 9;
    }

    pi_port::PiDonorHostContracts contracts;
    const auto& contract_state = contracts.bind(bridge);
    if (!contract_state.contracts_ready) {
        write_runtime_status(bridge_state, contract_state, {});
        return 10;
    }

    pi_port::PiDonorLiveRuntime runtime;
    const auto& runtime_state = runtime.start(bridge, contracts);
    write_runtime_status(bridge_state, contract_state, runtime_state);
    if (!runtime_state.runtime_ready) {
        return 11;
    }

    for (;;) {
        runtime.loop_once();
        delay(10);
    }
}