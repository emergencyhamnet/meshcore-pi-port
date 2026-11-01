#include "pi_gpio.h"

#include <array>
#include <cstdio>

#include <lgpio.h>

namespace pi_port {

namespace {

struct PinState {
    bool configured = false;
    GpioDirection direction = GpioDirection::input;
};

std::array<PinState, 64> g_pin_states{};
int g_gpio_handle = -1;

bool is_valid_pin(std::uint8_t pin) {
    return pin < g_pin_states.size();
}

} // namespace

bool gpio_init() {
    if (g_gpio_handle >= 0) {
        return true;
    }

    g_gpio_handle = lgGpiochipOpen(0);
    if (g_gpio_handle < 0) {
        std::fprintf(stderr, "PiGPIO: open GPIO chip failed: %s\n", lguErrorText(g_gpio_handle));
        return false;
    }
    return true;
}

bool gpio_configure_input(std::uint8_t pin) {
    if (g_gpio_handle < 0 || !is_valid_pin(pin)) {
        return false;
    }

    auto& state = g_pin_states[pin];
    if (state.configured && state.direction == GpioDirection::input) {
        return true;
    }
    if (state.configured) {
        lgGpioFree(g_gpio_handle, pin);
        state.configured = false;
    }
    const int result = lgGpioClaimInput(g_gpio_handle, 0, pin);
    if (result < 0) {
        std::fprintf(stderr, "PiGPIO: claim input GPIO %u failed: %s\n", pin, lguErrorText(result));
        return false;
    }
    state.configured = true;
    state.direction = GpioDirection::input;
    return true;
}

bool gpio_configure_output(std::uint8_t pin, bool initial_value) {
    if (g_gpio_handle < 0 || !is_valid_pin(pin)) {
        return false;
    }

    auto& state = g_pin_states[pin];
    if (state.configured && state.direction == GpioDirection::output) {
        return gpio_write(pin, initial_value);
    }
    if (state.configured) {
        lgGpioFree(g_gpio_handle, pin);
        state.configured = false;
    }
    const int result = lgGpioClaimOutput(g_gpio_handle, 0, pin, initial_value ? LG_HIGH : LG_LOW);
    if (result < 0) {
        std::fprintf(stderr, "PiGPIO: claim output GPIO %u failed: %s\n", pin, lguErrorText(result));
        return false;
    }
    state.configured = true;
    state.direction = GpioDirection::output;
    return true;
}

bool gpio_write(std::uint8_t pin, bool value) {
    if (g_gpio_handle < 0 || !is_valid_pin(pin)) {
        return false;
    }

    auto& state = g_pin_states[pin];
    if (!state.configured || state.direction != GpioDirection::output) {
        return false;
    }

    const int result = lgGpioWrite(g_gpio_handle, pin, value ? LG_HIGH : LG_LOW);
    if (result < 0) {
        std::fprintf(stderr, "PiGPIO: write GPIO %u failed: %s\n", pin, lguErrorText(result));
        return false;
    }
    return true;
}

bool gpio_read(std::uint8_t pin, bool& value) {
    if (g_gpio_handle < 0 || !is_valid_pin(pin)) {
        return false;
    }

    auto& state = g_pin_states[pin];
    if (!state.configured) {
        return false;
    }

    const int result = lgGpioRead(g_gpio_handle, pin);
    if (result < 0) {
        std::fprintf(stderr, "PiGPIO: read GPIO %u failed: %s\n", pin, lguErrorText(result));
        return false;
    }
    value = result != 0;
    return true;
}

} // namespace pi_port