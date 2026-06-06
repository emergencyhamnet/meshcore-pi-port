#include "pi_gpio.h"

#include <array>

namespace pi_port {

namespace {

struct PinState {
    bool configured = false;
    GpioDirection direction = GpioDirection::input;
    bool value = false;
};

std::array<PinState, 64> g_pin_states{};

bool is_valid_pin(std::uint8_t pin) {
    return pin < g_pin_states.size();
}

} // namespace

bool gpio_init() {
    return true;
}

bool gpio_configure_input(std::uint8_t pin) {
    if (!is_valid_pin(pin)) {
        return false;
    }

    g_pin_states[pin].configured = true;
    g_pin_states[pin].direction = GpioDirection::input;
    return true;
}

bool gpio_configure_output(std::uint8_t pin, bool initial_value) {
    if (!is_valid_pin(pin)) {
        return false;
    }

    g_pin_states[pin].configured = true;
    g_pin_states[pin].direction = GpioDirection::output;
    g_pin_states[pin].value = initial_value;
    return true;
}

bool gpio_write(std::uint8_t pin, bool value) {
    if (!is_valid_pin(pin)) {
        return false;
    }

    auto& state = g_pin_states[pin];
    if (!state.configured || state.direction != GpioDirection::output) {
        return false;
    }

    state.value = value;
    return true;
}

bool gpio_read(std::uint8_t pin, bool& value) {
    if (!is_valid_pin(pin)) {
        return false;
    }

    auto& state = g_pin_states[pin];
    if (!state.configured) {
        return false;
    }

    value = state.value;
    return true;
}

} // namespace pi_port