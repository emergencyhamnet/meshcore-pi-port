#include "pi_transport.h"

#include <algorithm>

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

} // namespace

PiTransportInterface::PiTransportInterface()
    : enabled_(false),
      connected_(false),
      state_(recv_state_idle),
      frame_len_(0),
      rx_len_(0),
      rx_frame_{} {}

bool PiTransportInterface::begin(const TransportEndpoint& endpoint) {
    endpoint_ = endpoint;
    connected_ = transport_ready(endpoint_);
    state_ = recv_state_idle;
    frame_len_ = 0;
    rx_len_ = 0;
    rx_bytes_.clear();
    tx_bytes_.clear();
    return connected_;
}

void PiTransportInterface::enable() {
    enabled_ = true;
    state_ = recv_state_idle;
}

void PiTransportInterface::disable() {
    enabled_ = false;
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

std::size_t PiTransportInterface::write_frame(const std::uint8_t src[], std::size_t len) {
    if (!enabled_ || !connected_ || len > max_transport_frame_size) {
        return 0;
    }

    tx_bytes_.push_back('>');
    tx_bytes_.push_back(static_cast<std::uint8_t>(len & 0xFF));
    tx_bytes_.push_back(static_cast<std::uint8_t>((len >> 8) & 0xFF));
    tx_bytes_.insert(tx_bytes_.end(), src, src + len);
    return len;
}

std::size_t PiTransportInterface::check_recv_frame(std::uint8_t dest[]) {
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