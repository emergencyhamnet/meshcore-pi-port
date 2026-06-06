#include "pi_donor_runtime_bridge.h"

int main() {
    pi_port::PiDonorRuntimeBridge bridge;
    const auto& state = bridge.start();

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

    return 0;
}