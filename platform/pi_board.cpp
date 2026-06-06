#include "pi_board.h"

#include "pi_gpio.h"

namespace pi_port {

namespace {

constexpr BoardProfile kBoardProfile{
    {
        BoardPins::nss,
        BoardPins::dio1,
        BoardPins::reset,
        BoardPins::busy,
        BoardPins::txen,
        BoardPins::rxen,
    },
    {
        BoardPins::spi_bus,
        8'000'000,
        0,
        8,
    },
    true,
};

} // namespace

const BoardProfile& board_profile() {
    return kBoardProfile;
}

bool board_bootstrap() {
    const auto& profile = board_profile();

    if (!gpio_configure_output(profile.radio.nss, true)) {
        return false;
    }
    if (!gpio_configure_input(profile.radio.dio1)) {
        return false;
    }
    if (!gpio_configure_output(profile.radio.reset, true)) {
        return false;
    }
    if (!gpio_configure_input(profile.radio.busy)) {
        return false;
    }
    if (!gpio_configure_output(profile.radio.txen, false)) {
        return false;
    }
    if (!gpio_configure_output(profile.radio.rxen, false)) {
        return false;
    }

    return true;
}

bool board_set_radio_path_mode(RadioPathMode mode) {
    const auto& profile = board_profile();

    switch (mode) {
    case RadioPathMode::standby:
        return gpio_write(profile.radio.txen, false) && gpio_write(profile.radio.rxen, false);
    case RadioPathMode::receive:
        return gpio_write(profile.radio.txen, false) && gpio_write(profile.radio.rxen, true);
    case RadioPathMode::transmit:
        return gpio_write(profile.radio.txen, true) && gpio_write(profile.radio.rxen, false);
    }

    return false;
}

bool board_pulse_radio_reset() {
    const auto& profile = board_profile();
    return gpio_write(profile.radio.reset, false) && gpio_write(profile.radio.reset, true);
}

bool board_read_radio_busy(bool& busy) {
    return gpio_read(board_profile().radio.busy, busy);
}

} // namespace pi_port