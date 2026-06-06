#include "pi_transport.h"

#include <algorithm>

#if defined(__linux__)
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <netdb.h>
#include <sys/socket.h>
#include <termios.h>
#include <unistd.h>
#endif

namespace pi_port {

namespace {

constexpr std::uint8_t recv_state_idle = 0;
constexpr std::uint8_t recv_state_hdr_found = 1;
constexpr std::uint8_t recv_state_len1_found = 2;
constexpr std::uint8_t recv_state_len2_found = 3;

bool starts_with(const std::string& value, const std::string& prefix) {
    return value.rfind(prefix, 0) == 0;
}

std::uint16_t parse_port(const std::string& value) {
    unsigned long parsed = 0;
    for (char ch : value) {
        if (ch < '0' || ch > '9') {
            return 0;
        }
        parsed = (parsed * 10) + static_cast<unsigned long>(ch - '0');
        if (parsed > 65535UL) {
            return 0;
        }
    }
    return static_cast<std::uint16_t>(parsed);
}

#if defined(__linux__)

bool set_nonblocking(int fd) {
    const int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) {
        return false;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK) == 0;
}

bool configure_serial_port(int fd) {
    struct termios options {};
    if (tcgetattr(fd, &options) != 0) {
        return false;
    }

    cfmakeraw(&options);
    cfsetispeed(&options, B115200);
    cfsetospeed(&options, B115200);
    options.c_cflag |= (CLOCAL | CREAD);
    options.c_cflag &= ~PARENB;
    options.c_cflag &= ~CSTOPB;
    options.c_cflag &= ~CSIZE;
    options.c_cflag |= CS8;

    return tcsetattr(fd, TCSANOW, &options) == 0;
}

int open_serial_transport(const TransportEndpoint& endpoint) {
    const int fd = open(endpoint.device.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) {
        return -1;
    }

    if (!configure_serial_port(fd)) {
        close(fd);
        return -1;
    }

    return fd;
}

int open_tcp_transport(const TransportEndpoint& endpoint) {
    struct addrinfo hints {};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    struct addrinfo* result = nullptr;
    const auto port = std::to_string(endpoint.port);
    if (getaddrinfo(endpoint.host.c_str(), port.c_str(), &hints, &result) != 0) {
        return -1;
    }

    int fd = -1;
    for (auto* it = result; it != nullptr; it = it->ai_next) {
        fd = socket(it->ai_family, it->ai_socktype, it->ai_protocol);
        if (fd < 0) {
            continue;
        }

        if (connect(fd, it->ai_addr, static_cast<int>(it->ai_addrlen)) == 0) {
            if (!set_nonblocking(fd)) {
                close(fd);
                fd = -1;
                continue;
            }
            break;
        }

        close(fd);
        fd = -1;
    }

    freeaddrinfo(result);
    return fd;
}

void close_transport_handle(int& fd) {
    if (fd >= 0) {
        close(fd);
        fd = -1;
    }
}

bool read_available_bytes(int fd, std::vector<std::uint8_t>& dest) {
    std::uint8_t buffer[256];
    bool read_any = false;
    while (true) {
        const auto count = read(fd, buffer, sizeof(buffer));
        if (count > 0) {
            dest.insert(dest.end(), buffer, buffer + count);
            read_any = true;
            continue;
        }
        if (count == 0) {
            return read_any;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return read_any;
        }
        return false;
    }
}

bool write_all_bytes(int fd, const std::uint8_t* src, std::size_t len) {
    std::size_t offset = 0;
    while (offset < len) {
        const auto count = write(fd, src + offset, len - offset);
        if (count > 0) {
            offset += static_cast<std::size_t>(count);
            continue;
        }
        if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            continue;
        }
        return false;
    }
    return true;
}

#endif

} // namespace

PiTransportInterface::PiTransportInterface()
    : enabled_(false),
      connected_(false),
      state_(recv_state_idle),
      frame_len_(0),
      rx_len_(0),
      rx_frame_{},
      native_handle_(-1) {}

PiTransportInterface::~PiTransportInterface() {
    disable();
}

bool PiTransportInterface::begin(const TransportEndpoint& endpoint) {
    disable();
    endpoint_ = endpoint;
    state_ = recv_state_idle;
    frame_len_ = 0;
    rx_len_ = 0;
    rx_bytes_.clear();
    tx_bytes_.clear();

    if (!transport_ready(endpoint_)) {
        connected_ = false;
        return false;
    }

#if defined(__linux__)
    switch (endpoint_.kind) {
    case TransportKind::serial:
        native_handle_ = open_serial_transport(endpoint_);
        break;
    case TransportKind::tcp:
        native_handle_ = open_tcp_transport(endpoint_);
        break;
    default:
        native_handle_ = -1;
        break;
    }
    connected_ = native_handle_ >= 0;
#else
    connected_ = transport_ready(endpoint_);
#endif

    return connected_;
}

void PiTransportInterface::enable() {
    enabled_ = true;
    state_ = recv_state_idle;
}

void PiTransportInterface::disable() {
    enabled_ = false;
#if defined(__linux__)
    close_transport_handle(native_handle_);
#endif
    connected_ = false;
}

bool PiTransportInterface::is_enabled() const {
    return enabled_;
}

bool PiTransportInterface::is_connected() const {
    return connected_;
}

bool PiTransportInterface::is_write_busy() const {
    return false;
}

int PiTransportInterface::native_handle() const {
    return native_handle_;
}

std::size_t PiTransportInterface::write_frame(const std::uint8_t src[], std::size_t len) {
    if (!enabled_ || !connected_ || len > max_transport_frame_size) {
        return 0;
    }

    std::vector<std::uint8_t> framed;
    framed.reserve(len + 3);
    framed.push_back('>');
    framed.push_back(static_cast<std::uint8_t>(len & 0xFF));
    framed.push_back(static_cast<std::uint8_t>((len >> 8) & 0xFF));
    framed.insert(framed.end(), src, src + len);

    tx_bytes_.insert(tx_bytes_.end(), framed.begin(), framed.end());

#if defined(__linux__)
    if (native_handle_ >= 0 && !write_all_bytes(native_handle_, framed.data(), framed.size())) {
        connected_ = false;
        return 0;
    }
#endif

    return len;
}

std::size_t PiTransportInterface::check_recv_frame(std::uint8_t dest[]) {
#if defined(__linux__)
    if (connected_ && native_handle_ >= 0 && !read_available_bytes(native_handle_, rx_bytes_)) {
        connected_ = false;
        return 0;
    }
#endif

    while (!rx_bytes_.empty()) {
        const std::uint8_t c = rx_bytes_.front();
        rx_bytes_.erase(rx_bytes_.begin());

        switch (state_) {
        case recv_state_idle:
            if (c == '<') {
                state_ = recv_state_hdr_found;
            }
            break;
        case recv_state_hdr_found:
            frame_len_ = c;
            state_ = recv_state_len1_found;
            break;
        case recv_state_len1_found:
            frame_len_ |= static_cast<std::uint16_t>(c) << 8;
            rx_len_ = 0;
            state_ = frame_len_ > 0 ? recv_state_len2_found : recv_state_idle;
            break;
        default:
            if (rx_len_ < max_transport_frame_size) {
                rx_frame_[rx_len_] = c;
            }
            ++rx_len_;
            if (rx_len_ >= frame_len_) {
                if (frame_len_ > max_transport_frame_size) {
                    frame_len_ = static_cast<std::uint16_t>(max_transport_frame_size);
                }
                std::copy(rx_frame_, rx_frame_ + frame_len_, dest);
                state_ = recv_state_idle;
                return frame_len_;
            }
            break;
        }
    }

    return 0;
}

void PiTransportInterface::inject_rx_bytes(const std::uint8_t src[], std::size_t len) {
    rx_bytes_.insert(rx_bytes_.end(), src, src + len);
}

const std::vector<std::uint8_t>& PiTransportInterface::tx_bytes() const {
    return tx_bytes_;
}

const TransportEndpoint& PiTransportInterface::endpoint() const {
    return endpoint_;
}

TransportEndpoint parse_transport_endpoint(const std::string& endpoint) {
    TransportEndpoint parsed{};
    parsed.kind = TransportKind::unknown;
    parsed.raw = endpoint;
    parsed.port = 0;

    if (starts_with(endpoint, "serial://")) {
        parsed.kind = TransportKind::serial;
        parsed.device = endpoint.substr(9);
        return parsed;
    }

    if (starts_with(endpoint, "tcp://")) {
        parsed.kind = TransportKind::tcp;
        const auto remainder = endpoint.substr(6);
        const auto colon = remainder.rfind(':');
        if (colon == std::string::npos) {
            return parsed;
        }
        parsed.host = remainder.substr(0, colon);
        parsed.port = parse_port(remainder.substr(colon + 1));
        return parsed;
    }

    return parsed;
}

bool transport_ready(const TransportEndpoint& endpoint) {
    switch (endpoint.kind) {
    case TransportKind::serial:
        return !endpoint.device.empty();
    case TransportKind::tcp:
        return !endpoint.host.empty() && endpoint.port != 0;
    default:
        return false;
    }
}

} // namespace pi_port