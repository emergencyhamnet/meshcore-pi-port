#include "pi_spi.h"

#include <array>

#include "pi_board.h"

namespace pi_port {

namespace {

SpiConfig g_spi_config = board_profile().spi;
bool g_spi_ready = false;

} // namespace

bool spi_init() {
    return spi_init(board_profile().spi);
}

bool spi_init(const SpiConfig& config) {
    g_spi_config = config;
    g_spi_ready = config.bits_per_word == 8;
    return g_spi_ready;
}

const SpiConfig& spi_bus_config() {
    return g_spi_config;
}

bool spi_transfer(const std::uint8_t* tx_buf, std::uint8_t* rx_buf, std::size_t size) {
    if (!g_spi_ready) {
        return false;
    }

    if (rx_buf == nullptr) {
        return true;
    }

    for (std::size_t index = 0; index < size; ++index) {
        rx_buf[index] = tx_buf == nullptr ? 0 : tx_buf[index];
    }

    return true;
}

} // namespace pi_port