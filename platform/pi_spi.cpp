#include "pi_spi.h"

namespace pi_port {

bool spi_init() {
    return true;
}

bool spi_transfer(const std::uint8_t*, std::uint8_t*, std::size_t) {
    return true;
}

} // namespace pi_port