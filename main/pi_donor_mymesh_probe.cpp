#include "pi_donor_mymesh_probe.h"

#include <cstring>

namespace {

PiProbeBoard g_probe_board;
PiProbeRadioDriver g_probe_radio_driver;
SensorManager g_probe_sensors;
unsigned long g_probe_millis = 0;

} // namespace

PiProbeBoard board = g_probe_board;
PiProbeRadioDriver radio_driver = g_probe_radio_driver;
SensorManager sensors = g_probe_sensors;

mesh::LocalIdentity radio_new_identity() {
    return mesh::LocalIdentity();
}

unsigned long millis() {
    return g_probe_millis++;
}

void randomSeed(long) {}

long random(long min_value, long) {
    return min_value;
}

namespace pi_port {

namespace {

constexpr std::uint8_t cmd_get_device_time = 5;
constexpr std::uint8_t cmd_app_start = 1;
constexpr std::uint8_t cmd_get_contacts = 4;
constexpr std::uint8_t cmd_device_query = 22;
constexpr std::uint8_t resp_code_contacts_start = 2;
constexpr std::uint8_t resp_code_contact = 3;
constexpr std::uint8_t resp_code_end_of_contacts = 4;
constexpr std::uint8_t resp_code_err = 1;
constexpr std::uint8_t resp_code_curr_time = 9;
constexpr std::uint8_t resp_code_self_info = 5;
constexpr std::uint8_t resp_code_device_info = 13;
constexpr std::uint8_t expected_adv_type_chat = 1;
constexpr std::uint8_t expected_firmware_ver_code = 13;
constexpr std::uint8_t expected_contact_slots = 50;
constexpr std::uint8_t expected_group_channels = 40;
constexpr std::uint8_t expected_max_lora_tx_power = 20;
constexpr std::uint32_t expected_ble_pin = 123456U;
constexpr std::int32_t expected_latitude_e6 = 51507400;
constexpr std::int32_t expected_longitude_e6 = -127800;
constexpr std::uint8_t expected_client_repeat = 2;
constexpr std::uint8_t expected_path_hash_mode = 1;
constexpr std::uint8_t expected_multi_acks = 1;
constexpr std::uint8_t expected_advert_loc_policy = 1;
constexpr std::uint8_t expected_telemetry_mode = 6;
constexpr std::uint8_t expected_manual_add_contacts = 1;
constexpr std::uint32_t expected_freq_khz = 915500U;
constexpr std::uint32_t expected_bw_khz = 250000U;
constexpr std::uint8_t expected_sf = 9;
constexpr std::uint8_t expected_cr = 5;
constexpr std::int8_t expected_tx_power_dbm = 17;
constexpr std::uint8_t expected_contact_type = 1;
constexpr std::uint8_t expected_contact_flags = 3;
constexpr std::uint8_t expected_contact_out_path_len = 4;
constexpr std::uint8_t expected_err_code_bad_state = 4;
constexpr std::uint32_t expected_contact_last_advert_timestamp = 123456U;
constexpr std::uint32_t expected_contact_lastmod = 654321U;
constexpr std::int32_t expected_contact_gps_lat = 51507400;
constexpr std::int32_t expected_contact_gps_lon = -127800;
constexpr char expected_build_date[] = "6 Jun 2026";
constexpr char expected_manufacturer[] = "PiProbe";
constexpr char expected_firmware_version[] = "v1.16.0";
constexpr char expected_node_name[] = "pi-port-probe";
constexpr char expected_contact_name[] = "probe-contact";

bool matches_device_time_reply(const std::vector<std::uint8_t>& bytes, std::size_t start, std::uint32_t expected_time) {
    if (bytes.size() < start + 8) {
        return false;
    }

    if (bytes[start] != '>') {
        return false;
    }

    const auto payload_len = static_cast<std::uint16_t>(bytes[start + 1])
        | (static_cast<std::uint16_t>(bytes[start + 2]) << 8);
    if (payload_len != 5) {
        return false;
    }

    if (bytes[start + 3] != resp_code_curr_time) {
        return false;
    }

    const auto observed_time = static_cast<std::uint32_t>(bytes[start + 4])
        | (static_cast<std::uint32_t>(bytes[start + 5]) << 8)
        | (static_cast<std::uint32_t>(bytes[start + 6]) << 16)
        | (static_cast<std::uint32_t>(bytes[start + 7]) << 24);
    return observed_time == expected_time;
}

bool matches_device_query_reply(const std::vector<std::uint8_t>& bytes, std::size_t start) {
    if (bytes.size() < start + 85) {
        return false;
    }

    if (bytes[start] != '>') {
        return false;
    }

    const auto payload_len = static_cast<std::uint16_t>(bytes[start + 1])
        | (static_cast<std::uint16_t>(bytes[start + 2]) << 8);
    if (payload_len != 82) {
        return false;
    }

    const auto* payload = &bytes[start + 3];
    if (payload[0] != resp_code_device_info
        || payload[1] != expected_firmware_ver_code
        || payload[2] != expected_contact_slots
        || payload[3] != expected_group_channels) {
        return false;
    }

    const auto observed_ble_pin = static_cast<std::uint32_t>(payload[4])
        | (static_cast<std::uint32_t>(payload[5]) << 8)
        | (static_cast<std::uint32_t>(payload[6]) << 16)
        | (static_cast<std::uint32_t>(payload[7]) << 24);
    if (observed_ble_pin != expected_ble_pin) {
        return false;
    }

    if (std::strncmp(reinterpret_cast<const char*>(&payload[8]), expected_build_date, 12) != 0) {
        return false;
    }

    if (std::strncmp(reinterpret_cast<const char*>(&payload[20]), expected_manufacturer, 40) != 0) {
        return false;
    }

    if (std::strncmp(reinterpret_cast<const char*>(&payload[60]), expected_firmware_version, 20) != 0) {
        return false;
    }

    return payload[80] == expected_client_repeat
        && payload[81] == expected_path_hash_mode;
}

bool matches_app_start_reply(const std::vector<std::uint8_t>& bytes, std::size_t start) {
    constexpr std::size_t expected_payload_len = 71;
    if (bytes.size() < start + 3 + expected_payload_len) {
        return false;
    }

    if (bytes[start] != '>') {
        return false;
    }

    const auto payload_len = static_cast<std::uint16_t>(bytes[start + 1])
        | (static_cast<std::uint16_t>(bytes[start + 2]) << 8);
    if (payload_len != expected_payload_len) {
        return false;
    }

    const auto* payload = &bytes[start + 3];
    if (payload[0] != resp_code_self_info
        || payload[1] != expected_adv_type_chat
        || payload[2] != static_cast<std::uint8_t>(expected_tx_power_dbm)
        || payload[3] != expected_max_lora_tx_power) {
        return false;
    }

    for (std::size_t index = 0; index < PUB_KEY_SIZE; ++index) {
        if (payload[4 + index] != 0) {
            return false;
        }
    }

    const auto observed_latitude = static_cast<std::int32_t>(
        static_cast<std::uint32_t>(payload[36])
        | (static_cast<std::uint32_t>(payload[37]) << 8)
        | (static_cast<std::uint32_t>(payload[38]) << 16)
        | (static_cast<std::uint32_t>(payload[39]) << 24));
    const auto observed_longitude = static_cast<std::int32_t>(
        static_cast<std::uint32_t>(payload[40])
        | (static_cast<std::uint32_t>(payload[41]) << 8)
        | (static_cast<std::uint32_t>(payload[42]) << 16)
        | (static_cast<std::uint32_t>(payload[43]) << 24));
    if (observed_latitude != expected_latitude_e6 || observed_longitude != expected_longitude_e6) {
        return false;
    }

    if (payload[44] != expected_multi_acks
        || payload[45] != expected_advert_loc_policy
        || payload[46] != expected_telemetry_mode
        || payload[47] != expected_manual_add_contacts) {
        return false;
    }

    const auto observed_freq = static_cast<std::uint32_t>(payload[48])
        | (static_cast<std::uint32_t>(payload[49]) << 8)
        | (static_cast<std::uint32_t>(payload[50]) << 16)
        | (static_cast<std::uint32_t>(payload[51]) << 24);
    const auto observed_bw = static_cast<std::uint32_t>(payload[52])
        | (static_cast<std::uint32_t>(payload[53]) << 8)
        | (static_cast<std::uint32_t>(payload[54]) << 16)
        | (static_cast<std::uint32_t>(payload[55]) << 24);
    if (observed_freq != expected_freq_khz || observed_bw != expected_bw_khz) {
        return false;
    }

    if (payload[56] != expected_sf || payload[57] != expected_cr) {
        return false;
    }

    return std::strncmp(reinterpret_cast<const char*>(&payload[58]), expected_node_name, sizeof(expected_node_name) - 1) == 0;
}

bool matches_contacts_reply_sequence(const std::vector<std::uint8_t>& bytes, std::size_t start) {
    constexpr std::size_t start_frame_size = 8;
    constexpr std::size_t contact_payload_len = 148;
    constexpr std::size_t contact_frame_size = 3 + contact_payload_len;
    constexpr std::size_t end_frame_size = 8;

    if (bytes.size() < start + start_frame_size + contact_frame_size + end_frame_size) {
        return false;
    }

    const auto read_u16 = [&bytes](std::size_t offset) {
        return static_cast<std::uint16_t>(bytes[offset])
            | (static_cast<std::uint16_t>(bytes[offset + 1]) << 8);
    };
    const auto read_u32 = [&bytes](std::size_t offset) {
        return static_cast<std::uint32_t>(bytes[offset])
            | (static_cast<std::uint32_t>(bytes[offset + 1]) << 8)
            | (static_cast<std::uint32_t>(bytes[offset + 2]) << 16)
            | (static_cast<std::uint32_t>(bytes[offset + 3]) << 24);
    };
    const auto read_i32 = [&read_u32](std::size_t offset) {
        return static_cast<std::int32_t>(read_u32(offset));
    };

    if (bytes[start] != '>' || read_u16(start + 1) != 5 || bytes[start + 3] != resp_code_contacts_start) {
        return false;
    }
    if (read_u32(start + 4) != 1U) {
        return false;
    }

    const auto contact_start = start + start_frame_size;
    if (bytes[contact_start] != '>' || read_u16(contact_start + 1) != contact_payload_len) {
        return false;
    }

    const auto* payload = &bytes[contact_start + 3];
    if (payload[0] != resp_code_contact) {
        return false;
    }

    for (std::size_t index = 0; index < PUB_KEY_SIZE; ++index) {
        if (payload[1 + index] != static_cast<std::uint8_t>(index + 16U)) {
            return false;
        }
    }

    if (payload[33] != expected_contact_type
        || payload[34] != expected_contact_flags
        || payload[35] != expected_contact_out_path_len) {
        return false;
    }

    for (std::size_t index = 0; index < MAX_PATH_SIZE; ++index) {
        const auto expected_path = index < expected_contact_out_path_len
            ? static_cast<std::uint8_t>(index + 1U)
            : 0U;
        if (payload[36 + index] != expected_path) {
            return false;
        }
    }

    if (std::strncmp(reinterpret_cast<const char*>(&payload[100]), expected_contact_name, sizeof(expected_contact_name) - 1) != 0) {
        return false;
    }

    if (read_u32(contact_start + 135) != expected_contact_last_advert_timestamp
        || read_i32(contact_start + 139) != expected_contact_gps_lat
        || read_i32(contact_start + 143) != expected_contact_gps_lon
        || read_u32(contact_start + 147) != expected_contact_lastmod) {
        return false;
    }

    const auto end_start = contact_start + contact_frame_size;
    if (bytes[end_start] != '>' || read_u16(end_start + 1) != 5 || bytes[end_start + 3] != resp_code_end_of_contacts) {
        return false;
    }
    return read_u32(end_start + 4) == expected_contact_lastmod;
}

bool matches_contacts_since_reply_sequence(const std::vector<std::uint8_t>& bytes, std::size_t start) {
    constexpr std::size_t frame_size = 8;

    if (bytes.size() < start + (2 * frame_size)) {
        return false;
    }

    const auto read_u16 = [&bytes](std::size_t offset) {
        return static_cast<std::uint16_t>(bytes[offset])
            | (static_cast<std::uint16_t>(bytes[offset + 1]) << 8);
    };
    const auto read_u32 = [&bytes](std::size_t offset) {
        return static_cast<std::uint32_t>(bytes[offset])
            | (static_cast<std::uint32_t>(bytes[offset + 1]) << 8)
            | (static_cast<std::uint32_t>(bytes[offset + 2]) << 16)
            | (static_cast<std::uint32_t>(bytes[offset + 3]) << 24);
    };

    if (bytes[start] != '>' || read_u16(start + 1) != 5 || bytes[start + 3] != resp_code_contacts_start) {
        return false;
    }
    if (read_u32(start + 4) != 1U) {
        return false;
    }

    const auto end_start = start + frame_size;
    if (bytes[end_start] != '>' || read_u16(end_start + 1) != 5 || bytes[end_start + 3] != resp_code_end_of_contacts) {
        return false;
    }
    return read_u32(end_start + 4) == 0U;
}

bool matches_contacts_busy_reply(const std::vector<std::uint8_t>& bytes, std::size_t start) {
    if (bytes.size() < start + 5) {
        return false;
    }

    const auto payload_len = static_cast<std::uint16_t>(bytes[start + 1])
        | (static_cast<std::uint16_t>(bytes[start + 2]) << 8);
    return bytes[start] == '>'
        && payload_len == 2
        && bytes[start + 3] == resp_code_err
        && bytes[start + 4] == expected_err_code_bad_state;
}

} // namespace

int PiDonorMyMeshProbe::ProbeRadio::recvRaw(uint8_t*, int) {
    return 0;
}

uint32_t PiDonorMyMeshProbe::ProbeRadio::getEstAirtimeFor(int) {
    return 0;
}

float PiDonorMyMeshProbe::ProbeRadio::packetScore(float, int) {
    return 0.0f;
}

bool PiDonorMyMeshProbe::ProbeRadio::startSendRaw(const uint8_t*, int) {
    return false;
}

bool PiDonorMyMeshProbe::ProbeRadio::isSendComplete() {
    return true;
}

void PiDonorMyMeshProbe::ProbeRadio::onSendFinished() {}

bool PiDonorMyMeshProbe::ProbeRadio::isInRecvMode() const {
    return true;
}

PiDonorMyMeshProbe::PiDonorMyMeshProbe()
    : radio_(),
      rng_(),
      tables_(),
      state_{},
      mesh_() {}

const DonorMyMeshProbeState& PiDonorMyMeshProbe::bind(PiDonorRuntimeBridge& bridge, PiDonorHostContracts& contracts, PiDonorDataStoreProbe& datastore_probe) {
    state_ = {};
    mesh_.reset();

    auto* store = datastore_probe.datastore();
    if (store == nullptr) {
        return state_;
    }

    mesh_ = std::make_unique<MyMesh>(radio_, rng_, contracts.donor_rtc_clock(), tables_, *store, nullptr);
    state_.mesh_constructed = mesh_ != nullptr;

    if (state_.mesh_constructed) {
        mesh_->begin(false);
        state_.begin_called = true;
        state_.node_name_loaded = std::strcmp(mesh_->getNodeName(), "pi-port-probe") == 0;
        state_.prefs_loaded = mesh_->getNodePrefs() != nullptr
            && std::strcmp(mesh_->getNodePrefs()->node_name, "pi-port-probe") == 0
            && mesh_->getNodePrefs()->freq == 915.5f;

        mesh_->startInterface(contracts.donor_serial_interface());
        state_.interface_started = true;
        state_.serial_enabled_after_start = contracts.serial_host().is_enabled();
        state_.prefs_pointer_ready = mesh_->getNodePrefs() != nullptr;

        constexpr std::uint32_t expected_time = 1700000000U;
        contracts.donor_rtc_clock().setCurrentTime(expected_time);

        const auto before_tx_size = bridge.adapter().transport().tx_bytes().size();
        const std::uint8_t command_frame[] = { '<', 1, 0, cmd_get_device_time };
        bridge.adapter().transport().inject_rx_bytes(command_frame, sizeof(command_frame));
        mesh_->loop();
        state_.command_loop_called = true;

        const auto& tx_bytes = bridge.adapter().transport().tx_bytes();
        state_.device_time_reply_ready = tx_bytes.size() >= before_tx_size + 8;
        state_.device_time_reply_valid = state_.device_time_reply_ready
            && matches_device_time_reply(tx_bytes, before_tx_size, expected_time);

        const auto before_device_query_tx_size = tx_bytes.size();
        const std::uint8_t device_query_frame[] = { '<', 2, 0, cmd_device_query, expected_firmware_ver_code };
        bridge.adapter().transport().inject_rx_bytes(device_query_frame, sizeof(device_query_frame));
        mesh_->loop();

        const auto& updated_tx_bytes = bridge.adapter().transport().tx_bytes();
        state_.device_query_reply_ready = updated_tx_bytes.size() >= before_device_query_tx_size + 85;
        state_.device_query_reply_valid = state_.device_query_reply_ready
            && matches_device_query_reply(updated_tx_bytes, before_device_query_tx_size);

        const auto before_app_start_tx_size = updated_tx_bytes.size();
        const std::uint8_t app_start_frame[] = { '<', 8, 0, cmd_app_start, 0, 0, 0, 0, 0, 0, 0 };
        bridge.adapter().transport().inject_rx_bytes(app_start_frame, sizeof(app_start_frame));
        mesh_->loop();

        const auto& final_tx_bytes = bridge.adapter().transport().tx_bytes();
        state_.app_start_reply_ready = final_tx_bytes.size() >= before_app_start_tx_size + 74;
        state_.app_start_reply_valid = state_.app_start_reply_ready
            && matches_app_start_reply(final_tx_bytes, before_app_start_tx_size);

        const std::uint8_t get_contacts_frame[] = { '<', 1, 0, cmd_get_contacts };
        bridge.adapter().transport().inject_rx_bytes(get_contacts_frame, sizeof(get_contacts_frame));
        mesh_->loop();

        const auto& contacts_busy_tx_bytes = bridge.adapter().transport().tx_bytes();
        const auto before_contacts_busy_err_tx_size = contacts_busy_tx_bytes.size();
        bridge.adapter().transport().inject_rx_bytes(get_contacts_frame, sizeof(get_contacts_frame));
        mesh_->loop();
        mesh_->loop();

        const auto& contacts_busy_err_tx_bytes = bridge.adapter().transport().tx_bytes();
        state_.contacts_busy_reply_ready = contacts_busy_err_tx_bytes.size() >= before_contacts_busy_err_tx_size + 5;
        state_.contacts_busy_reply_valid = state_.contacts_busy_reply_ready
            && matches_contacts_busy_reply(contacts_busy_err_tx_bytes, before_contacts_busy_err_tx_size);

        // Drain the iterator that was left running by the busy-state request path.
        mesh_->loop();

        const auto before_contacts_tx_size = bridge.adapter().transport().tx_bytes().size();
        bridge.adapter().transport().inject_rx_bytes(get_contacts_frame, sizeof(get_contacts_frame));
        mesh_->loop();
        mesh_->loop();
        mesh_->loop();

        const auto& contacts_tx_bytes = bridge.adapter().transport().tx_bytes();
        state_.contacts_reply_ready = contacts_tx_bytes.size() >= before_contacts_tx_size + 167;
        state_.contacts_reply_valid = state_.contacts_reply_ready
            && matches_contacts_reply_sequence(contacts_tx_bytes, before_contacts_tx_size);

        const auto before_contacts_since_tx_size = contacts_tx_bytes.size();
        const std::uint8_t contacts_since_frame[] = {
            '<', 5, 0, cmd_get_contacts,
            static_cast<std::uint8_t>((expected_contact_lastmod + 1U) & 0xFF),
            static_cast<std::uint8_t>(((expected_contact_lastmod + 1U) >> 8) & 0xFF),
            static_cast<std::uint8_t>(((expected_contact_lastmod + 1U) >> 16) & 0xFF),
            static_cast<std::uint8_t>(((expected_contact_lastmod + 1U) >> 24) & 0xFF)
        };
        bridge.adapter().transport().inject_rx_bytes(contacts_since_frame, sizeof(contacts_since_frame));
        mesh_->loop();
        mesh_->loop();
        mesh_->loop();

        const auto& contacts_since_tx_bytes = bridge.adapter().transport().tx_bytes();
        state_.contacts_since_reply_ready = contacts_since_tx_bytes.size() >= before_contacts_since_tx_size + 16;
        state_.contacts_since_reply_valid = state_.contacts_since_reply_ready
            && matches_contacts_since_reply_sequence(contacts_since_tx_bytes, before_contacts_since_tx_size);
    }

    state_.probe_ready = state_.mesh_constructed
        && state_.begin_called
        && state_.node_name_loaded
        && state_.prefs_loaded
        && state_.interface_started
        && state_.serial_enabled_after_start
        && state_.prefs_pointer_ready
        && state_.command_loop_called
        && state_.device_time_reply_ready
        && state_.device_time_reply_valid
        && state_.device_query_reply_ready
        && state_.device_query_reply_valid
        && state_.app_start_reply_ready
        && state_.app_start_reply_valid
        && state_.contacts_busy_reply_ready
        && state_.contacts_busy_reply_valid
        && state_.contacts_reply_ready
        && state_.contacts_reply_valid
        && state_.contacts_since_reply_ready
        && state_.contacts_since_reply_valid;
    return state_;
}

const DonorMyMeshProbeState& PiDonorMyMeshProbe::state() const {
    return state_;
}

MyMesh* PiDonorMyMeshProbe::mesh() {
    return mesh_.get();
}

} // namespace pi_port