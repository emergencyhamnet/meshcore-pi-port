#pragma once

#include <MeshCore.h>
#include <helpers/SensorManager.h>

class PiProbeBoard : public mesh::MainBoard {
public:
    uint16_t getBattMilliVolts() override { return 0; }
    const char* getManufacturerName() const override { return "PiProbe"; }
    void reboot() override {}
    uint8_t getStartupReason() const override { return mesh::BD_STARTUP_NORMAL; }
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
};

extern PiProbeBoard board;
extern PiProbeRadioDriver radio_driver;
extern SensorManager sensors;

mesh::LocalIdentity radio_new_identity();