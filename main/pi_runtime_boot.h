#pragma once

#include <string>

#include "../platform/pi_storage.h"

namespace pi_port {

struct RuntimeBootState {
    bool board_ready;
    bool gpio_ready;
    bool spi_ready;
    bool radio_path_ready;
    bool storage_ready;
    StorageLayout storage;
    std::string runtime_endpoint;
};

RuntimeBootState boot_runtime_state();

} // namespace pi_port