#include "pi_runtime_boot.h"

int main() {
    const auto state = pi_port::boot_runtime_state();

    if (!state.board_ready) {
        return 1;
    }

    if (!state.gpio_ready) {
        return 2;
    }

    if (!state.spi_ready) {
        return 3;
    }

    if (!state.radio_path_ready) {
        return 4;
    }

    if (!state.storage_ready) {
        return 5;
    }

    if (!state.transport_ready) {
        return 6;
    }

    return 0;
}