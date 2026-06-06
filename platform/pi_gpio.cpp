#include "pi_gpio.h"

namespace pi_port {

bool gpio_init() {
    return true;
}

bool gpio_write(std::uint8_t, bool) {
    return true;
}

bool gpio_read(std::uint8_t, bool& value) {
    value = false;
    return true;
}

} // namespace pi_port