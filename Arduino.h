#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

using byte = std::uint8_t;

unsigned long millis();
void randomSeed(long seed);
long random(long min_value, long max_value);

template <typename T>
constexpr T constrain(T value, T low, T high) {
	return value < low ? low : (value > high ? high : value);
}

#include "FS.h"
#include "Stream.h"