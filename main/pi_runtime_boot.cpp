#include "pi_runtime_boot.h"

#include <cstdlib>

#include "../platform/pi_board.h"
#include "../platform/pi_gpio.h"
#include "../platform/pi_spi.h"

namespace pi_port {

namespace {

std::string runtime_endpoint_from_env() {
    const char* endpoint = std::getenv("MESHCORE_PI_RUNTIME_ENDPOINT");
    if (endpoint == nullptr || *endpoint == '\0') {
        return "serial:///dev/ttyS0";
    }
    return endpoint;
}

} // namespace

RuntimeBootState boot_runtime_state() {
    RuntimeBootState state{};

    state.board_ready = board_bootstrap();
    if (!state.board_ready) {
        return state;
    }

    state.gpio_ready = gpio_init();
    if (!state.gpio_ready) {
        return state;
    }

    state.spi_ready = spi_init();
    if (!state.spi_ready) {
        return state;
    }

    state.radio_path_ready = board_set_radio_path_mode(RadioPathMode::standby);
    if (!state.radio_path_ready) {
        return state;
    }

    state.storage_ready = storage_init(&state.storage);
    state.runtime_endpoint = runtime_endpoint_from_env();
    return state;
}

} // namespace pi_port