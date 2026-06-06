#pragma once

#include <cstddef>
#include <cstdint>

namespace pi_port {

bool spi_init();
bool spi_transfer(const std::uint8_t* tx_buf, std::uint8_t* rx_buf, std::size_t size);

} // namespace pi_port