#include <chrono>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>

#include <MeshCore.h>

#include "../platform/pi_board.h"
#include "../platform/pi_gpio.h"
#include "../platform/pi_radiolib_hal.h"
#include "../src/helpers/radiolib/CustomSX1262.h"
#include "../src/helpers/radiolib/CustomSX1262Wrapper.h"

namespace {

class PiRadioLibSmokeBoard : public mesh::MainBoard {
public:
    uint16_t getBattMilliVolts() override { return 0; }
    const char* getManufacturerName() const override { return "PiRadioLib"; }
    void reboot() override {}
    uint8_t getStartupReason() const override { return BD_STARTUP_NORMAL; }
    uint32_t getIRQGpio() override { return pi_port::board_profile().radio.dio1; }

    void onBeforeTransmit() override {
        pi_port::board_set_radio_path_mode(pi_port::RadioPathMode::transmit);
    }

    void onAfterTransmit() override {
        pi_port::board_set_radio_path_mode(pi_port::RadioPathMode::receive);
    }
};

bool flag_equals(const char* value, const char* expected) {
    return value != nullptr && std::strcmp(value, expected) == 0;
}

} // namespace

int main(int argc, char** argv) {
    const auto& profile = pi_port::board_profile();

    if (!pi_port::gpio_init()) {
        std::fprintf(stderr, "pi-radiolib-smoke: gpio_init failed\n");
        return 1;
    }
    if (!pi_port::board_bootstrap()) {
        std::fprintf(stderr, "pi-radiolib-smoke: board bootstrap failed\n");
        return 2;
    }
    if (!pi_port::board_set_radio_path_mode(pi_port::RadioPathMode::standby)) {
        std::fprintf(stderr, "pi-radiolib-smoke: failed to set standby radio path\n");
        return 3;
    }

    pi_port::PiRadioLibHal hal(profile.spi.bus_index, profile.spi.frequency_hz);
    PiRadioLibSmokeBoard board;
    Module module(&hal, profile.radio.nss, profile.radio.dio1, profile.radio.reset, profile.radio.busy);
    CustomSX1262 radio(&module);
    CustomSX1262Wrapper radio_driver(radio, board);

    if (!radio.std_init()) {
        std::fprintf(stderr, "pi-radiolib-smoke: radio init failed\n");
        return 4;
    }

    radio_driver.begin();
    radio_driver.setParams(LORA_FREQ, LORA_BW, LORA_SF, LORA_CR);
    radio_driver.setTxPower(LORA_TX_POWER);

    if (!pi_port::board_set_radio_path_mode(pi_port::RadioPathMode::receive)) {
        std::fprintf(stderr, "pi-radiolib-smoke: failed to set receive radio path\n");
        return 5;
    }

    std::printf("pi-radiolib-smoke: radio init succeeded at %.3f MHz, bw %.1f kHz, sf %d, cr %d, tx %d dBm\n",
                static_cast<double>(LORA_FREQ),
                static_cast<double>(LORA_BW),
                static_cast<int>(LORA_SF),
                static_cast<int>(LORA_CR),
                static_cast<int>(LORA_TX_POWER));

    if (argc >= 3 && flag_equals(argv[1], "--tx")) {
        const std::string payload(argv[2]);
        if (!radio_driver.startSendRaw(reinterpret_cast<const uint8_t*>(payload.data()), static_cast<int>(payload.size()))) {
            std::fprintf(stderr, "pi-radiolib-smoke: transmit start failed\n");
            return 6;
        }

        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
        while (!radio_driver.isSendComplete()) {
            radio_driver.loop();
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            if (std::chrono::steady_clock::now() > deadline) {
                std::fprintf(stderr, "pi-radiolib-smoke: transmit timed out\n");
                return 7;
            }
        }

        radio_driver.onSendFinished();
        std::printf("pi-radiolib-smoke: transmitted %d bytes\n", static_cast<int>(payload.size()));
    } else {
        std::printf("pi-radiolib-smoke: init-only run complete. Pass --tx TEXT for one controlled burst.\n");
    }

    return 0;
}