#pragma once

#include <cstddef>
#include <cstdint>
#include <fstream>
#include <memory>
#include <string>

#include "Stream.h"

namespace pi_port {
class DonorStorageHost;
}

class File final : public Stream {
public:
    File();
    explicit operator bool() const;

    bool open_read(const std::string& path);
    bool open_write(const std::string& path, bool truncate);
    void close();

    int read() override;
    std::size_t read(std::uint8_t* buffer, std::size_t length);
    std::size_t write(std::uint8_t value) override;
    std::size_t write(const std::uint8_t* buffer, std::size_t length) override;

private:
    std::shared_ptr<std::fstream> stream_;
};

namespace fs {

class FS {
public:
    FS();

    void bind(pi_port::DonorStorageHost& storage_host, const std::string& root_path);
    bool is_bound() const;

    bool exists(const char* path) const;
    bool mkdir(const char* path);
    bool remove(const char* path);
    bool format();

    File open(const char* path);
    File open(const char* path, const char* mode);
    File open(const char* path, const char* mode, bool create);

private:
    std::string resolve_path(const char* path) const;

    pi_port::DonorStorageHost* storage_host_;
    std::string root_path_;
};

} // namespace fs