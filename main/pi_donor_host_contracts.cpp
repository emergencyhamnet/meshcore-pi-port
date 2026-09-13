#include "pi_donor_host_contracts.h"

#include <cstdarg>
#include <cstdio>
#include <ctime>
#include <filesystem>

#include "../platform/pi_board.h"
#include "../platform/pi_storage.h"

std::size_t Stream::printf(const char* format, ...) {
    if (format == nullptr) {
        return 0;
    }

    va_list args;
    va_start(args, format);
    va_list args_copy;
    va_copy(args_copy, args);
    const int required = std::vsnprintf(nullptr, 0, format, args_copy);
    va_end(args_copy);
    if (required <= 0) {
        va_end(args);
        return 0;
    }

    std::string buffer(static_cast<std::size_t>(required), '\0');
    std::vsnprintf(buffer.data(), buffer.size() + 1, format, args);
    va_end(args);
    return write(reinterpret_cast<const std::uint8_t*>(buffer.data()), buffer.size());
}

std::size_t Stream::print(const char* text) {
    if (text == nullptr) {
        return 0;
    }
    return write(reinterpret_cast<const std::uint8_t*>(text), std::char_traits<char>::length(text));
}

std::size_t Stream::println() {
    static const char newline[] = "\n";
    return print(newline);
}

std::size_t Stream::println(const char* text) {
    return print(text) + println();
}

File::File()
    : stream_(),
      directory_entries_(),
      directory_index_(0),
      is_directory_(false),
      path_(),
      name_() {}

File::operator bool() const {
    return is_directory_ || (stream_ != nullptr && stream_->is_open());
}

bool File::open_read(const std::string& path) {
    close();
    path_ = path;
    name_ = std::filesystem::path(path).filename().string();

    std::error_code error;
    if (std::filesystem::is_directory(path, error) && !error) {
        auto entries = std::make_shared<std::vector<std::filesystem::directory_entry>>();
        for (const auto& entry : std::filesystem::directory_iterator(path, error)) {
            if (error) {
                close();
                return false;
            }
            entries->push_back(entry);
        }
        directory_entries_ = std::move(entries);
        directory_index_ = 0;
        is_directory_ = true;
        return true;
    }

    stream_ = std::make_shared<std::fstream>(path, std::ios::in | std::ios::binary);
    return static_cast<bool>(*this);
}

bool File::open_write(const std::string& path, bool truncate) {
    close();
    path_ = path;
    name_ = std::filesystem::path(path).filename().string();
    auto open_mode = std::ios::out | std::ios::binary;
    if (truncate) {
        open_mode |= std::ios::trunc;
    }
    stream_ = std::make_shared<std::fstream>(path, open_mode);
    return static_cast<bool>(*this);
}

void File::close() {
    if (stream_ != nullptr) {
        stream_->close();
    }
    stream_.reset();
    directory_entries_.reset();
    directory_index_ = 0;
    is_directory_ = false;
    path_.clear();
    name_.clear();
}

int File::available() {
    if (!static_cast<bool>(*this) || is_directory_) {
        return 0;
    }

    const auto current = stream_->tellg();
    if (current < 0) {
        return 0;
    }

    stream_->seekg(0, std::ios::end);
    const auto end = stream_->tellg();
    stream_->seekg(current, std::ios::beg);
    if (end < current) {
        return 0;
    }
    return static_cast<int>(end - current);
}

int File::read() {
    if (!static_cast<bool>(*this) || is_directory_) {
        return -1;
    }

    const int value = stream_->get();
    return value == std::char_traits<char>::eof() ? -1 : value;
}

int File::peek() {
    if (!static_cast<bool>(*this) || is_directory_) {
        return -1;
    }

    const int value = stream_->peek();
    return value == std::char_traits<char>::eof() ? -1 : value;
}

std::size_t File::read(std::uint8_t* buffer, std::size_t length) {
    if (!static_cast<bool>(*this) || is_directory_ || buffer == nullptr) {
        return 0;
    }

    stream_->read(reinterpret_cast<char*>(buffer), static_cast<std::streamsize>(length));
    return static_cast<std::size_t>(stream_->gcount());
}

std::size_t File::write(std::uint8_t value) {
    if (!static_cast<bool>(*this) || is_directory_) {
        return 0;
    }

    stream_->put(static_cast<char>(value));
    return stream_->good() ? 1U : 0U;
}

std::size_t File::write(const std::uint8_t* buffer, std::size_t length) {
    if (!static_cast<bool>(*this) || is_directory_ || buffer == nullptr) {
        return 0;
    }

    stream_->write(reinterpret_cast<const char*>(buffer), static_cast<std::streamsize>(length));
    return stream_->good() ? length : 0U;
}

void File::flush() {
    if (stream_ != nullptr) {
        stream_->flush();
    }
}

bool File::isDirectory() const {
    return is_directory_;
}

const char* File::name() const {
    return name_.c_str();
}

std::uint32_t File::size() const {
    if (!static_cast<bool>(*this) || is_directory_ || path_.empty()) {
        return 0;
    }

    std::error_code error;
    const auto file_size = std::filesystem::file_size(path_, error);
    if (error) {
        return 0;
    }
    return static_cast<std::uint32_t>(file_size);
}

File File::openNextFile() {
    File next;
    if (!is_directory_ || directory_entries_ == nullptr) {
        return next;
    }

    while (directory_index_ < directory_entries_->size()) {
        const auto& entry = (*directory_entries_)[directory_index_++];
        if (next.open_read(entry.path().string())) {
            next.name_ = entry.path().filename().string();
            return next;
        }
    }

    return next;
}

void File::rewindDirectory() {
    if (is_directory_) {
        directory_index_ = 0;
    }
}

namespace fs {

FS::FS()
    : storage_host_(nullptr), root_path_() {}

void FS::bind(pi_port::DonorStorageHost& storage_host, const std::string& root_path) {
    storage_host_ = &storage_host;
    root_path_ = root_path;
}

bool FS::is_bound() const {
    return storage_host_ != nullptr && !root_path_.empty();
}

bool FS::exists(const char* path) const {
    if (!is_bound()) {
        return false;
    }

    std::error_code error;
    return std::filesystem::exists(resolve_path(path), error) && !error;
}

bool FS::mkdir(const char* path) {
    if (!is_bound()) {
        return false;
    }

    std::error_code error;
    std::filesystem::create_directories(resolve_path(path), error);
    return !error;
}

bool FS::remove(const char* path) {
    if (!is_bound()) {
        return false;
    }

    std::error_code error;
    return std::filesystem::remove(resolve_path(path), error) && !error;
}

bool FS::format() {
    if (!is_bound()) {
        return false;
    }

    std::error_code error;
    std::filesystem::remove_all(root_path_, error);
    if (error) {
        return false;
    }

    std::filesystem::create_directories(root_path_, error);
    return !error;
}

File FS::open(const char* path) {
    File file;
    file.open_read(resolve_path(path));
    return file;
}

File FS::open(const char* path, const char* mode) {
    return open(path, mode, false);
}

File FS::open(const char* path, const char* mode, bool create) {
    File file;
    const std::string resolved = resolve_path(path);
    const std::string open_mode = mode == nullptr ? std::string() : std::string(mode);
    const bool wants_write = open_mode.find('w') != std::string::npos;
    const bool wants_read = open_mode.empty() || open_mode.find('r') != std::string::npos;

    if (create || wants_write) {
        std::error_code error;
        std::filesystem::create_directories(std::filesystem::path(resolved).parent_path(), error);
        if (error) {
            return file;
        }
    }

    if (wants_write) {
        file.open_write(resolved, true);
        return file;
    }

    if (wants_read) {
        file.open_read(resolved);
    }

    return file;
}

std::string FS::resolve_path(const char* path) const {
    if (path == nullptr || *path == '\0') {
        return root_path_;
    }

    const std::string relative = path[0] == '/' ? std::string(path + 1) : std::string(path);
    return root_path_ + "/" + relative;
}

} // namespace fs

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
            current_time_offset_seconds_(0),
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

bool PiStorageHost::has_secondary_root() const {
    return boot_state_ != nullptr && !boot_state_->storage.channels.empty() && boot_state_->storage.channels != boot_state_->storage.root;
}

std::string PiStorageHost::secondary_root_path() const {
    return has_secondary_root() ? boot_state_->storage.channels : std::string();
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
    const std::int64_t system_time = static_cast<std::int64_t>(std::time(nullptr));
    if (!current_time_set_) {
        return static_cast<std::uint32_t>(system_time);
    }

    return static_cast<std::uint32_t>(system_time + current_time_offset_seconds_);
}

void PiStorageHost::set_current_time(std::uint32_t time) {
    const std::int64_t system_time = static_cast<std::int64_t>(std::time(nullptr));
    current_time_offset_seconds_ = static_cast<std::int64_t>(time) - system_time;
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
    donor_rtc_clock_impl_(),
    donor_primary_filesystem_impl_(),
    donor_secondary_filesystem_impl_() {}

const DonorHostContractsState& PiDonorHostContracts::bind(PiDonorRuntimeBridge& bridge) {
    state_ = {};

    const auto& bridge_state = bridge.state();

    board_host_impl_.bind(bridge_state.adapter.boot);
    storage_host_impl_.bind(bridge_state.adapter.boot);
    serial_host_impl_.bind(bridge.adapter().transport());
    donor_serial_interface_impl_.bind(serial_host_impl_);
    donor_rtc_clock_impl_.bind(storage_host_impl_);
    donor_primary_filesystem_impl_.bind(storage_host_impl_, storage_host_impl_.root_path());
    if (storage_host_impl_.has_secondary_root()) {
        donor_secondary_filesystem_impl_.bind(storage_host_impl_, storage_host_impl_.secondary_root_path());
    }

    state_.board_bound = board_host_impl_.is_ready();
    state_.storage_bound = storage_host_impl_.is_ready();
    state_.serial_bound = serial_host_impl_.is_ready();
    state_.donor_serial_interface_bound = true;
    state_.donor_rtc_clock_bound = true;
    state_.donor_primary_filesystem_bound = donor_primary_filesystem_impl_.is_bound();
    state_.donor_secondary_filesystem_bound = !storage_host_impl_.has_secondary_root() || donor_secondary_filesystem_impl_.is_bound();
    state_.contracts_ready = state_.board_bound && state_.storage_bound && state_.serial_bound && state_.donor_serial_interface_bound && state_.donor_rtc_clock_bound && state_.donor_primary_filesystem_bound && state_.donor_secondary_filesystem_bound;
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

fs::FS& PiDonorHostContracts::donor_primary_filesystem() {
    return donor_primary_filesystem_impl_;
}

fs::FS* PiDonorHostContracts::donor_secondary_filesystem() {
    if (!storage_host_impl_.has_secondary_root()) {
        return nullptr;
    }
    return &donor_secondary_filesystem_impl_;
}

} // namespace pi_port