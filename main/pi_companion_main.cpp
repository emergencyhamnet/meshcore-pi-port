#include "pi_runtime_adapter.h"

int main() {
    pi_port::PiRuntimeAdapter adapter;
    const auto& state = adapter.start();

    if (!state.boot.board_ready) {
        return 1;
    }

    if (!state.boot.gpio_ready) {
        return 2;
    }

    if (!state.boot.spi_ready) {
        return 3;
    }

    if (!state.boot.radio_path_ready) {
        return 4;
    }

    if (!state.boot.storage_ready) {
        return 5;
    }

    if (!state.boot.transport_ready) {
        return 6;
    }

    if (!state.transport_started) {
        return 7;
    }

    if (!state.transport_enabled) {
        return 8;
    }

    return 0;
}