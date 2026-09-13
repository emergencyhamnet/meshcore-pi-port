#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <type_traits>

#if defined(__linux__)
#include <unistd.h>
#endif

using byte = std::uint8_t;

unsigned long millis();
void randomSeed(long seed);
long random(long min_value, long max_value);
void delay(unsigned long millis_value);
char* ltoa(long value, char* buffer, int base);

template <typename T, typename U, typename V>
constexpr auto constrain(T value, U low, V high) -> std::common_type_t<T, U, V> {
	using Common = std::common_type_t<T, U, V>;
	const Common cast_value = static_cast<Common>(value);
	const Common cast_low = static_cast<Common>(low);
	const Common cast_high = static_cast<Common>(high);
	return cast_value < cast_low ? cast_low : (cast_value > cast_high ? cast_high : cast_value);
}

template <typename T, typename U>
constexpr auto min(T left, U right) -> std::common_type_t<T, U> {
	using Common = std::common_type_t<T, U>;
	return std::min(static_cast<Common>(left), static_cast<Common>(right));
}

#include "FS.h"
#include "Stream.h"

class HardwareSerial final : public Stream {
public:
	int read() override { return -1; }
	std::size_t write(std::uint8_t value) override {
		return std::fputc(static_cast<int>(value), stdout) == EOF ? 0U : 1U;
	}
	void flush() override {
		std::fflush(stdout);
	}
};

inline HardwareSerial Serial;

inline void delay(unsigned long millis_value) {
#if defined(__linux__)
	::usleep(millis_value * 1000U);
#else
	(void)millis_value;
#endif
}

inline char* ltoa(long value, char* buffer, int base) {
	if (buffer == nullptr || (base != 10 && base != 16)) {
		return buffer;
	}
	if (base == 10) {
		std::snprintf(buffer, 32, "%ld", value);
	} else {
		std::snprintf(buffer, 32, "%lx", static_cast<unsigned long>(value));
	}
	return buffer;
}