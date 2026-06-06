#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

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
    virtual std::string runtime_status_path() const = 0;
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

struct DonorHostContractsState {
    bool board_bound;
    bool storage_bound;
    bool serial_bound;
    bool donor_serial_interface_bound;
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
    std::string runtime_status_path() const override;

private:
    const RuntimeBootState* boot_state_;
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

private:
    DonorHostContractsState state_;
    PiBoardHost board_host_impl_;
    PiStorageHost storage_host_impl_;
    PiSerialHost serial_host_impl_;
    PiDonorSerialInterfaceAdapter donor_serial_interface_impl_;
};

} // namespace pi_port