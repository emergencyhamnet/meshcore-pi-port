#pragma once

#include <cstdint>

namespace pi_port {

bool gpio_init();
bool gpio_write(std::uint8_t pin, bool value);
bool gpio_read(std::uint8_t pin, bool& value);

} // namespace pi_port