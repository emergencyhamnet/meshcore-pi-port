#include "pi_donor_host_contracts.h"

#include <ctime>

#include "../platform/pi_board.h"
#include "../platform/pi_storage.h"

namespace pi_port {

PiDonorSerialInterfaceAdapter::PiDonorSerialInterfaceAdapter()
    : serial_host_(nullptr) {}

void PiDonorSerialInterfaceAdapter::bind(DonorSerialHost& serial_host) {
    serial_host_ = &serial_host;
}

void PiDonorSerialInterfaceAdapter::enable() {
    if (serial_host_ != nullptr) {
        serial_host_->enable();
    }
}

void PiDonorSerialInterfaceAdapter::disable() {
    if (serial_host_ != nullptr) {
        serial_host_->disable();
    }
}

bool PiDonorSerialInterfaceAdapter::isEnabled() const {
    return serial_host_ != nullptr && serial_host_->is_enabled();
}

bool PiDonorSerialInterfaceAdapter::isConnected() const {
    return serial_host_ != nullptr && serial_host_->is_connected();
}

bool PiDonorSerialInterfaceAdapter::isWriteBusy() const {
    return serial_host_ != nullptr && serial_host_->is_write_busy();
}

size_t PiDonorSerialInterfaceAdapter::writeFrame(const uint8_t src[], size_t len) {
    return serial_host_ == nullptr ? 0 : serial_host_->write_frame(src, len);
}

size_t PiDonorSerialInterfaceAdapter::checkRecvFrame(uint8_t dest[]) {
    return serial_host_ == nullptr ? 0 : serial_host_->check_recv_frame(dest);
}

PiDonorRTCClockAdapter::PiDonorRTCClockAdapter()
    : storage_host_(nullptr) {}

void PiDonorRTCClockAdapter::bind(DonorStorageHost& storage_host) {
    storage_host_ = &storage_host;
}

uint32_t PiDonorRTCClockAdapter::getCurrentTime() {
    return storage_host_ == nullptr ? 0 : storage_host_->get_current_time();
}

void PiDonorRTCClockAdapter::setCurrentTime(uint32_t time) {
    if (storage_host_ != nullptr) {
        storage_host_->set_current_time(time);
    }
}

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
        : boot_state_(nullptr),
            current_time_(0),
            current_time_set_(false) {}

void PiStorageHost::bind(const RuntimeBootState& boot_state) {
    boot_state_ = &boot_state;
}

bool PiStorageHost::is_ready() const {
    return boot_state_ != nullptr && boot_state_->storage_ready;
}

const StorageLayout& PiStorageHost::layout() const {
    return boot_state_->storage;
}

std::string PiStorageHost::root_path() const {
    return boot_state_ == nullptr ? std::string() : boot_state_->storage.root;
}

std::string PiStorageHost::identity_path() const {
    return boot_state_ == nullptr ? std::string() : boot_state_->storage.identity;
}

std::string PiStorageHost::state_path() const {
    return boot_state_ == nullptr ? std::string() : boot_state_->storage.state;
}

std::string PiStorageHost::channels_path() const {
    return boot_state_ == nullptr ? std::string() : boot_state_->storage.channels;
}

std::string PiStorageHost::runtime_status_path() const {
    return storage_runtime_status_path(boot_state_->storage);
}

std::uint32_t PiStorageHost::get_current_time() const {
    if (current_time_set_) {
        return current_time_;
    }

    return static_cast<std::uint32_t>(std::time(nullptr));
}

void PiStorageHost::set_current_time(std::uint32_t time) {
    current_time_ = time;
    current_time_set_ = true;
}

PiSerialHost::PiSerialHost()
    : transport_(nullptr) {}

void PiSerialHost::bind(PiTransportInterface& transport) {
    transport_ = &transport;
}

bool PiSerialHost::is_ready() const {
    return transport_ != nullptr && transport_->is_enabled() && transport_->is_connected();
}

void PiSerialHost::enable() {
    if (transport_ != nullptr) {
        transport_->enable();
    }
}

void PiSerialHost::disable() {
    if (transport_ != nullptr) {
        transport_->disable();
    }
}

bool PiSerialHost::is_enabled() const {
    return transport_ != nullptr && transport_->is_enabled();
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
    serial_host_impl_(),
    donor_serial_interface_impl_(),
    donor_rtc_clock_impl_() {}

const DonorHostContractsState& PiDonorHostContracts::bind(PiDonorRuntimeBridge& bridge) {
    state_ = {};

    const auto& bridge_state = bridge.state();

    board_host_impl_.bind(bridge_state.adapter.boot);
    storage_host_impl_.bind(bridge_state.adapter.boot);
    serial_host_impl_.bind(bridge.adapter().transport());
    donor_serial_interface_impl_.bind(serial_host_impl_);
    donor_rtc_clock_impl_.bind(storage_host_impl_);

    state_.board_bound = board_host_impl_.is_ready();
    state_.storage_bound = storage_host_impl_.is_ready();
    state_.serial_bound = serial_host_impl_.is_ready();
    state_.donor_serial_interface_bound = true;
    state_.donor_rtc_clock_bound = true;
    state_.contracts_ready = state_.board_bound && state_.storage_bound && state_.serial_bound && state_.donor_serial_interface_bound && state_.donor_rtc_clock_bound;
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

BaseSerialInterface& PiDonorHostContracts::donor_serial_interface() {
    return donor_serial_interface_impl_;
}

mesh::RTCClock& PiDonorHostContracts::donor_rtc_clock() {
    return donor_rtc_clock_impl_;
}

} // namespace pi_port