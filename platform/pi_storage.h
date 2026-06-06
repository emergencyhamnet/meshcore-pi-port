#pragma once

#include <string>

namespace pi_port {

struct StorageLayout {
	std::string root;
	std::string identity;
	std::string state;
	std::string channels;
	std::string logs;
};

std::string default_storage_root();
StorageLayout storage_layout();
bool storage_init(StorageLayout* layout = nullptr);

} // namespace pi_port