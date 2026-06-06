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
std::string storage_runtime_status_path(const StorageLayout& layout);
bool storage_write_text_file(const std::string& path, const std::string& content);
bool storage_read_text_file(const std::string& path, std::string* content);

} // namespace pi_port