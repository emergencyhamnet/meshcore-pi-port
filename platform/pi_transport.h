#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace pi_port {

constexpr std::size_t max_transport_frame_size = 176;

enum class TransportKind : std::uint8_t {
    unknown = 0,
    serial = 1,
    tcp = 2,
};

struct TransportEndpoint {
    TransportKind kind;
    std::string raw;
    std::string device;
    std::string host;
    std::uint16_t port;
};

class PiTransportInterface {
public:
    PiTransportInterface();
    ~PiTransportInterface();

    bool begin(const TransportEndpoint& endpoint);
    void enable();
    void disable();
    bool is_enabled() const;
    bool is_connected() const;
    bool is_write_busy() const;
    int native_handle() const;

    std::size_t write_frame(const std::uint8_t src[], std::size_t len);
    std::size_t check_recv_frame(std::uint8_t dest[]);

    void inject_rx_bytes(const std::uint8_t src[], std::size_t len);
    const std::vector<std::uint8_t>& tx_bytes() const;
    const TransportEndpoint& endpoint() const;

private:
    bool enabled_;
    bool connected_;
    std::uint8_t state_;
    std::uint16_t frame_len_;
    std::uint16_t rx_len_;
    std::vector<std::uint8_t> rx_bytes_;
    std::vector<std::uint8_t> tx_bytes_;
    std::uint8_t rx_frame_[max_transport_frame_size];
    TransportEndpoint endpoint_;
    int native_handle_;
};

TransportEndpoint parse_transport_endpoint(const std::string& endpoint);
bool transport_ready(const TransportEndpoint& endpoint);

} // namespace pi_port