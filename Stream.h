#pragma once

#include <cstddef>
#include <cstdarg>
#include <cstdint>

class Stream {
public:
    virtual ~Stream() = default;

    virtual int available() { return 0; }
    virtual int read() = 0;
    virtual int peek() { return -1; }
    virtual std::size_t write(std::uint8_t value) = 0;
    virtual void flush() {}

    virtual std::size_t readBytes(std::uint8_t* buffer, std::size_t length) {
        if (buffer == nullptr) {
            return 0;
        }

        std::size_t count = 0;
        while (count < length) {
            const int value = read();
            if (value < 0) {
                break;
            }
            buffer[count++] = static_cast<std::uint8_t>(value);
        }
        return count;
    }

    virtual std::size_t write(const std::uint8_t* buffer, std::size_t length) {
        if (buffer == nullptr) {
            return 0;
        }

        std::size_t count = 0;
        while (count < length) {
            count += write(buffer[count]);
        }
        return count;
    }

    std::size_t printf(const char* format, ...);
    std::size_t print(char value) { return write(static_cast<std::uint8_t>(value)); }
    std::size_t print(const char* text);
    std::size_t println();
    std::size_t println(char value) { return print(value) + println(); }
    std::size_t println(const char* text);
};