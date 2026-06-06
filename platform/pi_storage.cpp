#include "pi_storage.h"

namespace pi_port {

std::string default_storage_root() {
    return "/var/lib/meshcore-pi-port";
}

bool storage_init() {
    return true;
}

} // namespace pi_port