#include "pi_radiolib_hal.h"

#include <cinttypes>
#include <cstdio>
#include <thread>

#include "pi_board.h"
#include "pi_gpio.h"

namespace pi_port {

namespace {

bool is_hardware_spi_chip_select(std::uint32_t pin) {
    return pin == board_profile().radio.nss;
}

bool is_board_rf_switch_pin(std::uint32_t pin) {
    return pin == board_profile().radio.txen || pin == board_profile().radio.rxen;
}

} // namespace

PiRadioLibHal::PiRadioLibHal(std::uint8_t spi_channel,
                             std::uint32_t spi_speed_hz,
                             std::uint8_t spi_device,
                             std::uint8_t gpio_chip)
    : RadioLibHal(kInput, kOutput, kLow, kHigh, kRising, kFalling),
      gpio_chip_(gpio_chip),
      spi_device_(spi_device),
      spi_speed_hz_(spi_speed_hz),
      spi_channel_(spi_channel),
      gpio_handle_(-1),
      spi_handle_(-1),
      pin_flags_{},
    pin_claimed_{},
    pin_modes_{},
      interrupt_enabled_{},
      interrupt_levels_{},
      interrupt_callbacks_{},
      start_time_(std::chrono::steady_clock::now()) {}

PiRadioLibHal::~PiRadioLibHal() {
    term();
}

void PiRadioLibHal::init() {
    if (gpio_handle_ >= 0) {
        return;
    }

    gpio_handle_ = lgGpiochipOpen(gpio_chip_);
    if (gpio_handle_ < 0) {
        report_error("open GPIO chip", gpio_handle_);
        return;
    }

    spiBegin();
}

void PiRadioLibHal::term() {
    spiEnd();

    if (gpio_handle_ >= 0) {
        lgGpiochipClose(gpio_handle_);
        gpio_handle_ = -1;
    }

    pin_claimed_.fill(false);
    pin_modes_.fill(0);
}

void PiRadioLibHal::pinMode(std::uint32_t pin, std::uint32_t mode) {
    if (pin == RADIOLIB_NC || !is_valid_gpio(pin) || gpio_handle_ < 0) {
        return;
    }

    if (is_hardware_spi_chip_select(pin)) {
        return;
    }

    if (is_board_rf_switch_pin(pin)) {
        bool configured = false;
        if (mode == GpioModeInput) {
            configured = gpio_configure_input(static_cast<std::uint8_t>(pin));
        } else if (mode == GpioModeOutput) {
            configured = gpio_configure_output(static_cast<std::uint8_t>(pin), false);
        } else {
            std::fprintf(stderr, "PiRadioLibHal: unsupported pinMode(%" PRIu32 ") on GPIO %" PRIu32 "\n", mode, pin);
            return;
        }

        if (!configured) {
            std::fprintf(stderr,
                         "PiRadioLibHal: configure GPIO %" PRIu32 " via board GPIO failed\n",
                         pin);
            return;
        }

        pin_claimed_[pin] = true;
        pin_modes_[pin] = mode;
        return;
    }

    if (pin_claimed_[pin] && pin_modes_[pin] == mode) {
        return;
    }

    if (pin_claimed_[pin]) {
        lgGpioFree(gpio_handle_, pin);
        pin_claimed_[pin] = false;
    }

    int result = 0;
    if (mode == GpioModeInput) {
        result = lgGpioClaimInput(gpio_handle_, pin_flags_[pin], pin);
    } else if (mode == GpioModeOutput) {
        result = lgGpioClaimOutput(gpio_handle_, pin_flags_[pin], pin, LG_HIGH);
    } else {
        std::fprintf(stderr, "PiRadioLibHal: unsupported pinMode(%" PRIu32 ") on GPIO %" PRIu32 "\n", mode, pin);
        return;
    }

    if (result < 0) {
        std::fprintf(stderr,
                     "PiRadioLibHal: configure GPIO %" PRIu32 " failed: %s\n",
                     pin,
                     lguErrorText(result));
        return;
    }

    pin_claimed_[pin] = true;
    pin_modes_[pin] = mode;
}

void PiRadioLibHal::digitalWrite(std::uint32_t pin, std::uint32_t value) {
    if (pin == RADIOLIB_NC || !is_valid_gpio(pin) || gpio_handle_ < 0) {
        return;
    }

    if (is_hardware_spi_chip_select(pin)) {
        return;
    }

    if (is_board_rf_switch_pin(pin)) {
        if (!pin_claimed_[pin]) {
            pinMode(pin, GpioModeOutput);
            if (!pin_claimed_[pin]) {
                return;
            }
        }

        if (!gpio_write(static_cast<std::uint8_t>(pin), value != 0)) {
            std::fprintf(stderr,
                         "PiRadioLibHal: write GPIO %" PRIu32 " via board GPIO failed\n",
                         pin);
        }
        return;
    }

    const int result = lgGpioWrite(gpio_handle_, pin, static_cast<int>(value));
    if (result < 0) {
        std::fprintf(stderr,
                     "PiRadioLibHal: write GPIO %" PRIu32 " failed: %s\n",
                     pin,
                     lguErrorText(result));
    }
}

std::uint32_t PiRadioLibHal::digitalRead(std::uint32_t pin) {
    if (pin == RADIOLIB_NC || !is_valid_gpio(pin) || gpio_handle_ < 0) {
        return 0;
    }

    if (is_board_rf_switch_pin(pin)) {
        bool value = false;
        if (!pin_claimed_[pin]) {
            pinMode(pin, GpioModeInput);
            if (!pin_claimed_[pin]) {
                return 0;
            }
        }

        if (!gpio_read(static_cast<std::uint8_t>(pin), value)) {
            return 0;
        }

        return value ? 1U : 0U;
    }
    
    if (!pin_claimed_[pin]) {
        pinMode(pin, GpioModeInput);
        if (!pin_claimed_[pin]) {
            return 0;
        }
    }

    const int result = lgGpioRead(gpio_handle_, pin);
    if (result < 0) {
        std::fprintf(stderr,
                     "PiRadioLibHal: read GPIO %" PRIu32 " failed: %s\n",
                     pin,
                     lguErrorText(result));
        return 0;
    }

    return static_cast<std::uint32_t>(result);
}

void PiRadioLibHal::attachInterrupt(std::uint32_t interrupt_num,
                                    void (*interrupt_cb)(void),
                                    std::uint32_t mode) {
    if (interrupt_num == RADIOLIB_NC || !is_valid_gpio(interrupt_num) || gpio_handle_ < 0) {
        return;
    }

    const int result = lgGpioClaimAlert(gpio_handle_, 0, static_cast<int>(mode), interrupt_num, -1);
    if (result < 0) {
        report_error("claim GPIO alert", result);
        return;
    }

    interrupt_enabled_[interrupt_num] = true;
    interrupt_levels_[interrupt_num] = mode == GpioInterruptFalling ? LG_LOW : LG_HIGH;
    interrupt_callbacks_[interrupt_num] = interrupt_cb;
    lgGpioSetAlertsFunc(gpio_handle_, interrupt_num, gpio_alert_handler, this);
}

void PiRadioLibHal::detachInterrupt(std::uint32_t interrupt_num) {
    if (interrupt_num == RADIOLIB_NC || !is_valid_gpio(interrupt_num) || gpio_handle_ < 0) {
        return;
    }

    interrupt_enabled_[interrupt_num] = false;
    interrupt_levels_[interrupt_num] = 0;
    interrupt_callbacks_[interrupt_num] = nullptr;
    lgGpioSetAlertsFunc(gpio_handle_, interrupt_num, nullptr, nullptr);
    lgGpioFree(gpio_handle_, interrupt_num);
    pin_claimed_[interrupt_num] = false;
    pin_modes_[interrupt_num] = 0;
}

void PiRadioLibHal::delay(RadioLibTime_t ms) {
    if (ms == 0) {
        yield();
        return;
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}

void PiRadioLibHal::delayMicroseconds(RadioLibTime_t us) {
    if (us == 0) {
        yield();
        return;
    }

    std::this_thread::sleep_for(std::chrono::microseconds(us));
}

RadioLibTime_t PiRadioLibHal::millis() {
    const auto elapsed = std::chrono::steady_clock::now() - start_time_;
    return static_cast<RadioLibTime_t>(std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count());
}

RadioLibTime_t PiRadioLibHal::micros() {
    const auto elapsed = std::chrono::steady_clock::now() - start_time_;
    return static_cast<RadioLibTime_t>(std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count());
}

long PiRadioLibHal::pulseIn(std::uint32_t pin, std::uint32_t state, RadioLibTime_t timeout) {
    if (pin == RADIOLIB_NC || !is_valid_gpio(pin)) {
        return 0;
    }

    const RadioLibTime_t start = micros();
    while (digitalRead(pin) == state) {
        if (micros() - start > timeout) {
            return 0;
        }
        yield();
    }

    while (digitalRead(pin) != state) {
        if (micros() - start > timeout) {
            return 0;
        }
        yield();
    }

    const RadioLibTime_t pulse_start = micros();
    while (digitalRead(pin) == state) {
        if (micros() - pulse_start > timeout) {
            return 0;
        }
        yield();
    }

    return static_cast<long>(micros() - pulse_start);
}

void PiRadioLibHal::spiBegin() {
    if (spi_handle_ >= 0) {
        return;
    }

    spi_handle_ = lgSpiOpen(spi_device_, spi_channel_, spi_speed_hz_, 0);
    if (spi_handle_ < 0) {
        report_error("open SPI", spi_handle_);
    }
}

void PiRadioLibHal::spiBeginTransaction() {}

void PiRadioLibHal::spiTransfer(std::uint8_t* out, std::size_t len, std::uint8_t* in) {
    if (spi_handle_ < 0) {
        return;
    }

    const int result = lgSpiXfer(
        spi_handle_,
        reinterpret_cast<char*>(out),
        reinterpret_cast<char*>(in),
        static_cast<std::uint32_t>(len));
    if (result < 0) {
        report_error("SPI transfer", result);
    }
}

void PiRadioLibHal::spiEndTransaction() {}

void PiRadioLibHal::spiEnd() {
    if (spi_handle_ >= 0) {
        lgSpiClose(spi_handle_);
        spi_handle_ = -1;
    }
}

void PiRadioLibHal::yield() {
    std::this_thread::yield();
}

void PiRadioLibHal::tone(std::uint32_t, unsigned int, RadioLibTime_t) {}

void PiRadioLibHal::noTone(std::uint32_t) {}

void PiRadioLibHal::pullUpDown(std::uint32_t pin, bool enable, bool up) {
    if (pin == RADIOLIB_NC || !is_valid_gpio(pin)) {
        return;
    }

#if LGPIO_VERSION >= 0x00020200
    pin_flags_[pin] = enable ? (up ? LG_SET_PULL_UP : LG_SET_PULL_DOWN) : LG_SET_PULL_NONE;
#else
    (void)enable;
    (void)up;
#endif
}

void PiRadioLibHal::gpio_alert_handler(int num_alerts, lgGpioAlert_p alerts, void* userdata) {
    auto* hal = static_cast<PiRadioLibHal*>(userdata);
    if (hal == nullptr) {
        return;
    }

    for (lgGpioAlert_t* alert = alerts; alert < alerts + num_alerts; ++alert) {
        const std::uint32_t gpio = alert->report.gpio;
        if (!hal->is_valid_gpio(gpio)) {
            continue;
        }
        if (!hal->interrupt_enabled_[gpio]) {
            continue;
        }
        if (hal->interrupt_levels_[gpio] != static_cast<std::uint32_t>(alert->report.level)) {
            continue;
        }
        auto callback = hal->interrupt_callbacks_[gpio];
        if (callback != nullptr) {
            callback();
        }
    }
}

void PiRadioLibHal::report_error(const char* action, int result) const {
    std::fprintf(stderr, "PiRadioLibHal: %s failed: %s\n", action, lguErrorText(result));
}

bool PiRadioLibHal::is_valid_gpio(std::uint32_t pin) const {
    return pin <= kMaxUserGpio;
}

} // namespace pi_port