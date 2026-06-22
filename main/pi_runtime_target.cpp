#include "../target.h"

#if defined(MESHCORE_PI_LIVE_RADIO)

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <ctime>

#include "../platform/pi_board.h"

namespace {

struct PiHatTelemetrySnapshot {
    bool battery_valid = false;
    float battery_voltage_v = 0.0f;
    bool temperature_valid = false;
    float temperature_c = 0.0f;
    bool humidity_valid = false;
    float humidity_pct = 0.0f;
    bool pressure_valid = false;
    float pressure_hpa = 0.0f;
};

struct PiHatTelemetryConfig {
    std::string snapshot_path = "/tmp/meshcore-pi-telemetry.env";
    int snapshot_max_age_seconds = 60;
    bool battery_enabled = true;
    bool temperature_enabled = true;
    bool humidity_enabled = true;
    bool pressure_enabled = true;
};

int env_int(const char* name, int fallback) {
    const char* value = std::getenv(name);
    if (value == nullptr || *value == '\0') {
        return fallback;
    }

    char* end = nullptr;
    const long parsed = std::strtol(value, &end, 0);
    if (end == value) {
        return fallback;
    }
    return static_cast<int>(parsed);
}

float env_float(const char* name, float fallback) {
    const char* value = std::getenv(name);
    if (value == nullptr || *value == '\0') {
        return fallback;
    }

    char* end = nullptr;
    const float parsed = std::strtof(value, &end);
    if (end == value) {
        return fallback;
    }
    return parsed;
}

std::string env_string(const char* name, const char* fallback) {
    const char* value = std::getenv(name);
    if (value == nullptr || *value == '\0') {
        return std::string(fallback);
    }
    return std::string(value);
}

std::string env_string_compat(const char* primary_name, const char* legacy_name, const char* fallback) {
    const std::string primary = env_string(primary_name, "");
    if (!primary.empty()) {
        return primary;
    }
    const std::string legacy = env_string(legacy_name, "");
    if (!legacy.empty()) {
        return legacy;
    }
    return std::string(fallback);
}

int env_int_compat(const char* primary_name, const char* legacy_name, int fallback) {
    const char* primary = std::getenv(primary_name);
    if (primary != nullptr && *primary != '\0') {
        return env_int(primary_name, fallback);
    }
    const char* legacy = std::getenv(legacy_name);
    if (legacy != nullptr && *legacy != '\0') {
        return env_int(legacy_name, fallback);
    }
    return fallback;
}

bool env_bool(const char* name, bool fallback) {
    const char* value = std::getenv(name);
    if (value == nullptr || *value == '\0') {
        return fallback;
    }

    if (std::strcmp(value, "1") == 0 || std::strcmp(value, "true") == 0 || std::strcmp(value, "TRUE") == 0 ||
        std::strcmp(value, "yes") == 0 || std::strcmp(value, "YES") == 0 || std::strcmp(value, "on") == 0 ||
        std::strcmp(value, "ON") == 0) {
        return true;
    }
    if (std::strcmp(value, "0") == 0 || std::strcmp(value, "false") == 0 || std::strcmp(value, "FALSE") == 0 ||
        std::strcmp(value, "no") == 0 || std::strcmp(value, "NO") == 0 || std::strcmp(value, "off") == 0 ||
        std::strcmp(value, "OFF") == 0) {
        return false;
    }
    return fallback;
}

PiHatTelemetryConfig load_pi_hat_telemetry_config() {
    PiHatTelemetryConfig config;
    config.snapshot_path = env_string_compat(
        "MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH",
        "MESHCORE_PI_BASESTATION_SNAPSHOT_PATH",
        config.snapshot_path.c_str());
    config.snapshot_max_age_seconds = env_int_compat(
        "MESHCORE_PI_TELEMETRY_SNAPSHOT_MAX_AGE_SECONDS",
        "MESHCORE_PI_BASESTATION_SNAPSHOT_MAX_AGE_SECONDS",
        config.snapshot_max_age_seconds);
    config.battery_enabled = env_bool("MESHCORE_PI_HAT_ENABLE_BATTERY", config.battery_enabled);
    config.temperature_enabled = env_bool("MESHCORE_PI_HAT_ENABLE_TEMPERATURE", config.temperature_enabled);
    config.humidity_enabled = env_bool("MESHCORE_PI_HAT_ENABLE_HUMIDITY", config.humidity_enabled);
    config.pressure_enabled = env_bool("MESHCORE_PI_HAT_ENABLE_PRESSURE", config.pressure_enabled);
    return config;
}

class PiHatTelemetryReader {
public:
    PiHatTelemetryReader() : config_(load_pi_hat_telemetry_config()) {}

    std::uint16_t battery_millivolts() const {
        PiHatTelemetrySnapshot snapshot;
        if (!read(snapshot) || !snapshot.battery_valid) {
            return 0;
        }
        const float millivolts = snapshot.battery_voltage_v * 1000.0f;
        if (!std::isfinite(millivolts) || millivolts <= 0.0f) {
            return 0;
        }
        return static_cast<std::uint16_t>(std::lround(millivolts));
    }

    bool read(PiHatTelemetrySnapshot& snapshot) const {
        snapshot = {};
        if (config_.snapshot_path.empty()) {
            return false;
        }

        std::ifstream input(config_.snapshot_path);
        if (!input.is_open()) {
            return false;
        }

        std::time_t timestamp_unix = 0;
        std::string line;
        while (std::getline(input, line)) {
            const std::size_t sep = line.find('=');
            if (sep == std::string::npos) {
                continue;
            }

            const std::string key = line.substr(0, sep);
            const std::string value = line.substr(sep + 1);
            if (key == "timestamp_unix") {
                timestamp_unix = static_cast<std::time_t>(std::strtoll(value.c_str(), nullptr, 10));
            } else if (key == "temperature_c" && !value.empty() && config_.temperature_enabled) {
                snapshot.temperature_c = std::strtof(value.c_str(), nullptr);
                snapshot.temperature_valid = std::isfinite(snapshot.temperature_c);
            } else if (key == "humidity_pct" && !value.empty() && config_.humidity_enabled) {
                snapshot.humidity_pct = std::strtof(value.c_str(), nullptr);
                snapshot.humidity_valid = std::isfinite(snapshot.humidity_pct);
            } else if (key == "pressure_hpa" && !value.empty() && config_.pressure_enabled) {
                snapshot.pressure_hpa = std::strtof(value.c_str(), nullptr);
                snapshot.pressure_valid = std::isfinite(snapshot.pressure_hpa);
            } else if (key == "vbat_v" && !value.empty() && config_.battery_enabled) {
                snapshot.battery_voltage_v = std::strtof(value.c_str(), nullptr);
                snapshot.battery_valid = std::isfinite(snapshot.battery_voltage_v) && snapshot.battery_voltage_v > 0.0f;
            }
        }

        const std::time_t now = std::time(nullptr);
        if (timestamp_unix <= 0 || (config_.snapshot_max_age_seconds > 0 && now - timestamp_unix > config_.snapshot_max_age_seconds)) {
            return false;
        }

        return snapshot.battery_valid || snapshot.temperature_valid || snapshot.humidity_valid || snapshot.pressure_valid;
    }

private:
    PiHatTelemetryConfig config_;
};

class PiHatSensorManager final : public SensorManager {
public:
    explicit PiHatSensorManager(PiHatTelemetryReader& reader) : reader_(reader) {}

    bool begin() override { return true; }

    bool querySensors(uint8_t requester_permissions, CayenneLPP& telemetry) override {
        if ((requester_permissions & TELEM_PERM_ENVIRONMENT) == 0) {
            return false;
        }

        PiHatTelemetrySnapshot snapshot;
        if (!reader_.read(snapshot)) {
            std::fprintf(stderr, "PiHat telemetry read failed\n");
            return false;
        }

        std::fprintf(
            stderr,
            "PiHat telemetry snapshot batt_valid=%d batt_v=%.3f temp_valid=%d temp_c=%.2f hum_valid=%d hum_pct=%.2f pressure_valid=%d pressure_hpa=%.2f\n",
            snapshot.battery_valid ? 1 : 0,
            snapshot.battery_voltage_v,
            snapshot.temperature_valid ? 1 : 0,
            snapshot.temperature_c,
            snapshot.humidity_valid ? 1 : 0,
            snapshot.humidity_pct,
            snapshot.pressure_valid ? 1 : 0,
            snapshot.pressure_hpa);

        const std::uint8_t channel = TELEM_CHANNEL_SELF + 1;
        if (snapshot.temperature_valid) {
            telemetry.addTemperature(channel, snapshot.temperature_c);
        }
        if (snapshot.humidity_valid) {
            telemetry.addRelativeHumidity(channel, snapshot.humidity_pct);
        }
        if (snapshot.pressure_valid) {
            telemetry.addBarometricPressure(channel, snapshot.pressure_hpa);
        }
        return snapshot.temperature_valid || snapshot.humidity_valid || snapshot.pressure_valid;
    }

private:
    PiHatTelemetryReader& reader_;
};

pi_port::PiRadioLibHal g_hal(
    pi_port::board_profile().spi.bus_index,
    pi_port::board_profile().spi.frequency_hz);
Module g_module(
    &g_hal,
    pi_port::board_profile().radio.nss,
    pi_port::board_profile().radio.dio1,
    pi_port::board_profile().radio.reset,
    pi_port::board_profile().radio.busy);
CustomSX1262 g_radio(&g_module);
std::chrono::steady_clock::time_point g_start_time = std::chrono::steady_clock::now();
PiHatTelemetryReader g_hat_telemetry;
PiHatSensorManager g_sensors(g_hat_telemetry);

} // namespace

PiLiveBoard board;
CustomSX1262Wrapper radio_driver(g_radio, board);
SensorManager& sensors = g_sensors;

uint16_t PiLiveBoard::getBattMilliVolts() {
    return g_hat_telemetry.battery_millivolts();
}

bool radio_init() {
    board.begin();

    if (!pi_port::board_set_radio_path_mode(pi_port::RadioPathMode::standby)) {
        return false;
    }

    if (!g_radio.std_init()) {
        return false;
    }

    radio_driver.begin();
    return pi_port::board_set_radio_path_mode(pi_port::RadioPathMode::receive);
}

mesh::LocalIdentity radio_new_identity() {
    RadioNoiseListener rng(g_radio);
    return mesh::LocalIdentity(&rng);
}

unsigned long millis() {
    const auto elapsed = std::chrono::steady_clock::now() - g_start_time;
    return static_cast<unsigned long>(std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count());
}

void randomSeed(long seed) {
    std::srand(static_cast<unsigned int>(seed));
}

long random(long min_value, long max_value) {
    if (max_value <= min_value) {
        return min_value;
    }

    const auto range = static_cast<unsigned long>(max_value - min_value);
    return min_value + static_cast<long>(std::rand() % range);
}

#else

PiProbeBoard board;
PiProbeRadioDriver radio_driver;
SensorManager g_probe_sensors;
SensorManager& sensors = g_probe_sensors;

mesh::LocalIdentity radio_new_identity() {
    return mesh::LocalIdentity();
}

#endif