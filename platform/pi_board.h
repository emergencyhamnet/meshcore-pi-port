#pragma once

#include <cstdint>

namespace pi_port {

struct BoardPins {
    static constexpr std::uint8_t nss = 8;
    static constexpr std::uint8_t dio1 = 25;
    static constexpr std::uint8_t reset = 17;
    static constexpr std::uint8_t busy = 24;
    static constexpr std::uint8_t txen = 22;
    static constexpr std::uint8_t rxen = 27;
    static constexpr std::uint8_t spi_bus = 0;
};

bool board_bootstrap();

} // namespace pi_port