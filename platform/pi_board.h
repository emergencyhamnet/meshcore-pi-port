#pragma once

#include <cstdint>

namespace pi_port {

enum class RadioPathMode : std::uint8_t {
    standby = 0,
    receive = 1,
    transmit = 2,
};

struct RadioPins {
    std::uint8_t nss;
    std::uint8_t dio1;
    std::uint8_t reset;
    std::uint8_t busy;
    std::uint8_t txen;
    std::uint8_t rxen;
};

struct SpiConfig {
    std::uint8_t bus_index;
    std::uint32_t frequency_hz;
    std::uint8_t mode;
    std::uint8_t bits_per_word;
};

struct BoardProfile {
    RadioPins radio;
    SpiConfig spi;
    bool has_explicit_rf_switch;
};

struct BoardPins {
    static constexpr std::uint8_t nss = 8;
    static constexpr std::uint8_t dio1 = 25;
    static constexpr std::uint8_t reset = 17;
    static constexpr std::uint8_t busy = 24;
    static constexpr std::uint8_t txen = 22;
    static constexpr std::uint8_t rxen = 27;
    static constexpr std::uint8_t spi_bus = 0;
};

const BoardProfile& board_profile();
bool board_bootstrap();
bool board_set_radio_path_mode(RadioPathMode mode);
bool board_pulse_radio_reset();
bool board_read_radio_busy(bool& busy);

} // namespace pi_port