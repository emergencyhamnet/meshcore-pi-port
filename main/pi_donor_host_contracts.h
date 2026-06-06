#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

#include "../src/MeshCore.h"
#include "../src/helpers/BaseSerialInterface.h"
#include "pi_donor_runtime_bridge.h"

namespace pi_port {

class DonorBoardHost {
public:
    virtual ~DonorBoardHost() = default;
    virtual bool is_ready() const = 0;
    virtual const BoardProfile& profile() const = 0;
    virtual bool set_radio_path_mode(RadioPathMode mode) = 0;
    virtual bool pulse_radio_reset() = 0;
    virtual bool read_radio_busy(bool& busy) const = 0;
};

class DonorStorageHost {
public:
    virtual ~DonorStorageHost() = default;
    virtual bool is_ready() const = 0;
    virtual const StorageLayout& layout() const = 0;
    virtual std::string root_path() const = 0;
    virtual std::string identity_path() const = 0;
    virtual std::string state_path() const = 0;
    virtual std::string channels_path() const = 0;
    virtual std::string runtime_status_path() const = 0;
    virtual std::uint32_t get_current_time() const = 0;
    virtual void set_current_time(std::uint32_t time) = 0;
};

class DonorSerialHost {
public:
    virtual ~DonorSerialHost() = default;
    virtual bool is_ready() const = 0;
    virtual void enable() = 0;
    virtual void disable() = 0;
    virtual bool is_enabled() const = 0;
    virtual bool is_connected() const = 0;
    virtual bool is_write_busy() const = 0;
    virtual std::size_t write_frame(const std::uint8_t src[], std::size_t len) = 0;
    virtual std::size_t check_recv_frame(std::uint8_t dest[]) = 0;
};

class PiDonorSerialInterfaceAdapter final : public BaseSerialInterface {
public:
    PiDonorSerialInterfaceAdapter();
    void bind(DonorSerialHost& serial_host);

    void enable() override;
    void disable() override;
    bool isEnabled() const override;
    bool isConnected() const override;
    bool isWriteBusy() const override;
    size_t writeFrame(const uint8_t src[], size_t len) override;
    size_t checkRecvFrame(uint8_t dest[]) override;

private:
    DonorSerialHost* serial_host_;
};

class PiDonorRTCClockAdapter final : public mesh::RTCClock {
public:
    PiDonorRTCClockAdapter();
    void bind(DonorStorageHost& storage_host);

    uint32_t getCurrentTime() override;
    void setCurrentTime(uint32_t time) override;

private:
    DonorStorageHost* storage_host_;
};

struct DonorHostContractsState {
    bool board_bound;
    bool storage_bound;
    bool serial_bound;
    bool donor_serial_interface_bound;
    bool donor_rtc_clock_bound;
    bool contracts_ready;
};

class PiBoardHost final : public DonorBoardHost {
public:
    PiBoardHost();
    void bind(const RuntimeBootState& boot_state);

    bool is_ready() const override;
    const BoardProfile& profile() const override;
    bool set_radio_path_mode(RadioPathMode mode) override;
    bool pulse_radio_reset() override;
    bool read_radio_busy(bool& busy) const override;

private:
    const RuntimeBootState* boot_state_;
};

class PiStorageHost final : public DonorStorageHost {
public:
    PiStorageHost();
    void bind(const RuntimeBootState& boot_state);

    bool is_ready() const override;
    const StorageLayout& layout() const override;
    std::string root_path() const override;
    std::string identity_path() const override;
    std::string state_path() const override;
    std::string channels_path() const override;
    std::string runtime_status_path() const override;
    std::uint32_t get_current_time() const override;
    void set_current_time(std::uint32_t time) override;

private:
    const RuntimeBootState* boot_state_;
    std::uint32_t current_time_;
    bool current_time_set_;
};

class PiSerialHost final : public DonorSerialHost {
public:
    PiSerialHost();
    void bind(PiTransportInterface& transport);

    bool is_ready() const override;
    void enable() override;
    void disable() override;
    bool is_enabled() const override;
    bool is_connected() const override;
    bool is_write_busy() const override;
    std::size_t write_frame(const std::uint8_t src[], std::size_t len) override;
    std::size_t check_recv_frame(std::uint8_t dest[]) override;

private:
    PiTransportInterface* transport_;
};

class PiDonorHostContracts {
public:
    PiDonorHostContracts();

    const DonorHostContractsState& bind(PiDonorRuntimeBridge& bridge);
    const DonorHostContractsState& state() const;
    DonorBoardHost& board_host();
    DonorStorageHost& storage_host();
    DonorSerialHost& serial_host();
    BaseSerialInterface& donor_serial_interface();
    mesh::RTCClock& donor_rtc_clock();

private:
    DonorHostContractsState state_;
    PiBoardHost board_host_impl_;
    PiStorageHost storage_host_impl_;
    PiSerialHost serial_host_impl_;
    PiDonorSerialInterfaceAdapter donor_serial_interface_impl_;
    PiDonorRTCClockAdapter donor_rtc_clock_impl_;
};

} // namespace pi_port