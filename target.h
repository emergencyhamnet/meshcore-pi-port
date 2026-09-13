#pragma once

#include <MeshCore.h>
#include <helpers/SensorManager.h>

#if defined(MESHCORE_PI_LIVE_RADIO)

#define RADIOLIB_STATIC_ONLY 1

#include "platform/pi_board.h"
#include "platform/pi_radiolib_hal.h"
#include "src/helpers/radiolib/CustomSX1262Wrapper.h"

class PiLiveBoard : public mesh::MainBoard {
public:
    void begin() {}

    uint16_t getBattMilliVolts() override;
    const char* getManufacturerName() const override { return "Raspberry Pi"; }
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

extern PiLiveBoard board;
extern CustomSX1262Wrapper radio_driver;
extern SensorManager& sensors;

bool radio_init();
mesh::LocalIdentity radio_new_identity();

#else

class PiProbeBoard : public mesh::MainBoard {
public:
    uint16_t getBattMilliVolts() override { return 0; }
    const char* getManufacturerName() const override { return "PiProbe"; }
    void reboot() override {}
    uint8_t getStartupReason() const override { return BD_STARTUP_NORMAL; }
};

class PiProbeRadioDriver : public mesh::Radio {
public:
    int recvRaw(uint8_t*, int) override { return 0; }
    uint32_t getEstAirtimeFor(int) override { return 0; }
    float packetScore(float, int) override { return 0.0f; }
    bool startSendRaw(const uint8_t*, int) override { return false; }
    bool isSendComplete() override { return true; }
    void onSendFinished() override {}
    bool isInRecvMode() const override { return true; }

    void setParams(float, float, uint8_t, uint8_t) {}
    void setTxPower(int8_t) {}
    void setRxBoostedGainMode(uint8_t) {}
    bool getRxBoostedGainMode() const { return false; }
    long getRngSeed() const { return 1; }
    float getLastSNR() const { return 0.0f; }
    float getLastRSSI() const { return 0.0f; }
    uint32_t getPacketsRecv() const { return 0; }
    uint32_t getPacketsSent() const { return 0; }
    uint32_t getPacketsRecvErrors() const { return 0; }
};

extern PiProbeBoard board;
extern PiProbeRadioDriver radio_driver;
extern SensorManager& sensors;

mesh::LocalIdentity radio_new_identity();

#endif
