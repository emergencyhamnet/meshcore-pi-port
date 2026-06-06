#include "pi_storage.h"

#include <cstdlib>
#include <filesystem>

namespace pi_port {

namespace {

std::string env_or_empty(const char* name) {
    const char* value = std::getenv(name);
    if (value == nullptr) {
        return {};
    }
    return value;
}

bool ensure_directory(const std::string& path) {
    if (path.empty()) {
        return false;
    }

    std::error_code error;
    std::filesystem::create_directories(path, error);
    return !error;
}

} // namespace

std::string default_storage_root() {
    auto configured_root = env_or_empty("MESHCORE_PI_STORAGE_ROOT");
    if (!configured_root.empty()) {
        return configured_root;
    }

    auto legacy_root = env_or_empty("MESHCORE_PI_IDENTITY_PATH");
    if (!legacy_root.empty()) {
        return legacy_root;
    }

    return "/var/lib/meshcore-pi-port";
}

StorageLayout storage_layout() {
    const auto root = default_storage_root();
    return {
        root,
        root + "/identity",
        root + "/state",
        root + "/channels",
        root + "/logs",
    };
}

bool storage_init(StorageLayout* layout) {
    const auto resolved = storage_layout();

    if (!ensure_directory(resolved.root)) {
        return false;
    }
    if (!ensure_directory(resolved.identity)) {
        return false;
    }
    if (!ensure_directory(resolved.state)) {
        return false;
    }
    if (!ensure_directory(resolved.channels)) {
        return false;
    }
    if (!ensure_directory(resolved.logs)) {
        return false;
    }

    if (layout != nullptr) {
        *layout = resolved;
    }

    return true;
}

} // namespace pi_port