#pragma once

#include <cstdint>

namespace pi_port {

enum class GpioDirection : std::uint8_t {
	input = 0,
	output = 1,
};

bool gpio_init();
bool gpio_configure_input(std::uint8_t pin);
bool gpio_configure_output(std::uint8_t pin, bool initial_value);
bool gpio_write(std::uint8_t pin, bool value);
bool gpio_read(std::uint8_t pin, bool& value);

} // namespace pi_port