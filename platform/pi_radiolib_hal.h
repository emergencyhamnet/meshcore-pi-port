#pragma once

#define RADIOLIB_STATIC_ONLY 1

#include <RadioLib.h>
#include <lgpio.h>

#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>

namespace pi_port {

class PiRadioLibHal : public RadioLibHal {
public:
    static constexpr std::uint32_t kInput = 0;
    static constexpr std::uint32_t kOutput = 1;
    static constexpr std::uint32_t kLow = 0;
    static constexpr std::uint32_t kHigh = 1;
    static constexpr std::uint32_t kRising = LG_RISING_EDGE;
    static constexpr std::uint32_t kFalling = LG_FALLING_EDGE;
    static constexpr std::uint32_t kMaxUserGpio = 31;

    PiRadioLibHal(std::uint8_t spi_channel,
                  std::uint32_t spi_speed_hz = 2'000'000U,
                  std::uint8_t spi_device = 0,
                  std::uint8_t gpio_chip = 0);
    ~PiRadioLibHal() override;

    void init() override;
    void term() override;

    void pinMode(std::uint32_t pin, std::uint32_t mode) override;
    void digitalWrite(std::uint32_t pin, std::uint32_t value) override;
    std::uint32_t digitalRead(std::uint32_t pin) override;
    void attachInterrupt(std::uint32_t interrupt_num, void (*interrupt_cb)(void), std::uint32_t mode) override;
    void detachInterrupt(std::uint32_t interrupt_num) override;
    void delay(RadioLibTime_t ms) override;
    void delayMicroseconds(RadioLibTime_t us) override;
    RadioLibTime_t millis() override;
    RadioLibTime_t micros() override;
    long pulseIn(std::uint32_t pin, std::uint32_t state, RadioLibTime_t timeout) override;
    void spiBegin() override;
    void spiBeginTransaction() override;
    void spiTransfer(std::uint8_t* out, std::size_t len, std::uint8_t* in) override;
    void spiEndTransaction() override;
    void spiEnd() override;
    void yield() override;
    void tone(std::uint32_t pin, unsigned int frequency, RadioLibTime_t duration = 0) override;
    void noTone(std::uint32_t pin) override;
    void pullUpDown(std::uint32_t pin, bool enable, bool up) override;

private:
    using InterruptCallback = void (*)(void);

    static void gpio_alert_handler(int num_alerts, lgGpioAlert_p alerts, void* userdata);
    void report_error(const char* action, int result) const;
    bool is_valid_gpio(std::uint32_t pin) const;

    const std::uint8_t gpio_chip_;
    const std::uint8_t spi_device_;
    const std::uint32_t spi_speed_hz_;
    const std::uint8_t spi_channel_;
    int gpio_handle_;
    int spi_handle_;
    std::array<int, kMaxUserGpio + 1> pin_flags_;
    std::array<bool, kMaxUserGpio + 1> pin_claimed_;
    std::array<std::uint32_t, kMaxUserGpio + 1> pin_modes_;
    std::array<bool, kMaxUserGpio + 1> interrupt_enabled_;
    std::array<std::uint32_t, kMaxUserGpio + 1> interrupt_levels_;
    std::array<InterruptCallback, kMaxUserGpio + 1> interrupt_callbacks_;
    std::chrono::steady_clock::time_point start_time_;
};

} // namespace pi_port