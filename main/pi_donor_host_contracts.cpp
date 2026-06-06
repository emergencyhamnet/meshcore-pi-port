#include "pi_donor_host_contracts.h"

#include "../platform/pi_board.h"
#include "../platform/pi_storage.h"

namespace pi_port {

PiBoardHost::PiBoardHost()
    : boot_state_(nullptr) {}

void PiBoardHost::bind(const RuntimeBootState& boot_state) {
    boot_state_ = &boot_state;
}

bool PiBoardHost::is_ready() const {
    return boot_state_ != nullptr && boot_state_->board_ready && boot_state_->radio_path_ready;
}

const BoardProfile& PiBoardHost::profile() const {
    return board_profile();
}

bool PiBoardHost::set_radio_path_mode(RadioPathMode mode) {
    return board_set_radio_path_mode(mode);
}

bool PiBoardHost::pulse_radio_reset() {
    return board_pulse_radio_reset();
}

bool PiBoardHost::read_radio_busy(bool& busy) const {
    return board_read_radio_busy(busy);
}

PiStorageHost::PiStorageHost()
    : boot_state_(nullptr) {}

void PiStorageHost::bind(const RuntimeBootState& boot_state) {
    boot_state_ = &boot_state;
}

bool PiStorageHost::is_ready() const {
    return boot_state_ != nullptr && boot_state_->storage_ready;
}

const StorageLayout& PiStorageHost::layout() const {
    return boot_state_->storage;
}

std::string PiStorageHost::runtime_status_path() const {
    return storage_runtime_status_path(boot_state_->storage);
}

PiSerialHost::PiSerialHost()
    : transport_(nullptr) {}

void PiSerialHost::bind(PiTransportInterface& transport) {
    transport_ = &transport;
}

bool PiSerialHost::is_ready() const {
    return transport_ != nullptr && transport_->is_enabled() && transport_->is_connected();
}

bool PiSerialHost::is_connected() const {
    return transport_ != nullptr && transport_->is_connected();
}

bool PiSerialHost::is_write_busy() const {
    return transport_ != nullptr && transport_->is_write_busy();
}

std::size_t PiSerialHost::write_frame(const std::uint8_t src[], std::size_t len) {
    return transport_ == nullptr ? 0 : transport_->write_frame(src, len);
}

std::size_t PiSerialHost::check_recv_frame(std::uint8_t dest[]) {
    return transport_ == nullptr ? 0 : transport_->check_recv_frame(dest);
}

PiDonorHostContracts::PiDonorHostContracts()
    : state_{},
    board_host_impl_(),
    storage_host_impl_(),
    serial_host_impl_() {}

const DonorHostContractsState& PiDonorHostContracts::bind(PiDonorRuntimeBridge& bridge) {
    state_ = {};

    const auto& bridge_state = bridge.state();

    board_host_impl_.bind(bridge_state.adapter.boot);
    storage_host_impl_.bind(bridge_state.adapter.boot);
    serial_host_impl_.bind(bridge.adapter().transport());

    state_.board_bound = board_host_impl_.is_ready();
    state_.storage_bound = storage_host_impl_.is_ready();
    state_.serial_bound = serial_host_impl_.is_ready();
    state_.contracts_ready = state_.board_bound && state_.storage_bound && state_.serial_bound;
    return state_;
}

const DonorHostContractsState& PiDonorHostContracts::state() const {
    return state_;
}

DonorBoardHost& PiDonorHostContracts::board_host() {
    return board_host_impl_;
}

DonorStorageHost& PiDonorHostContracts::storage_host() {
    return storage_host_impl_;
}

DonorSerialHost& PiDonorHostContracts::serial_host() {
    return serial_host_impl_;
}

} // namespace pi_port