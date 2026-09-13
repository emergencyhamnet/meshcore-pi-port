#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

class CayenneLPP {
public:
	explicit CayenneLPP(std::size_t max_size = 230)
		: length_(0),
		  max_size_(max_size < sizeof(buffer_) ? max_size : sizeof(buffer_)) {}

	void reset() {
		length_ = 0;
	}

	bool addVoltage(std::uint8_t channel, float voltage) {
		return append_scaled_2(channel, 116, voltage, 100.0f, false);
	}

	bool addTemperature(std::uint8_t channel, float temperature) {
		return append_scaled_2(channel, 103, temperature, 10.0f, true);
	}

	bool addRelativeHumidity(std::uint8_t channel, float humidity) {
		if (length_ + 3 > max_size_) {
			return false;
		}
		buffer_[length_++] = channel;
		buffer_[length_++] = 104;
		buffer_[length_++] = static_cast<std::uint8_t>(humidity * 2.0f);
		return true;
	}

	bool addBarometricPressure(std::uint8_t channel, float pressure_hpa) {
		return append_scaled_2(channel, 115, pressure_hpa, 10.0f, false);
	}

	bool addGPS(std::uint8_t channel, float latitude, float longitude, float altitude) {
		if (length_ + 11 > max_size_) {
			return false;
		}
		buffer_[length_++] = channel;
		buffer_[length_++] = 136;
		append_int24(static_cast<std::int32_t>(latitude * 10000.0f));
		append_int24(static_cast<std::int32_t>(longitude * 10000.0f));
		append_int24(static_cast<std::int32_t>(altitude * 100.0f));
		return true;
	}

	bool addAnalogInput(std::uint8_t channel, float value) {
		return append_scaled_2(channel, 2, value, 100.0f, true);
	}

	bool addAnalogOutput(std::uint8_t channel, float value) {
		return append_scaled_2(channel, 3, value, 100.0f, true);
	}

	bool addLuminosity(std::uint8_t channel, std::uint16_t value) {
		return append_uint16(channel, 101, value);
	}

	bool addPresence(std::uint8_t channel, bool present) {
		if (length_ + 3 > max_size_) {
			return false;
		}
		buffer_[length_++] = channel;
		buffer_[length_++] = 102;
		buffer_[length_++] = present ? 1U : 0U;
		return true;
	}

	std::uint8_t getSize() const {
		return static_cast<std::uint8_t>(length_);
	}

	std::uint8_t* getBuffer() {
		return buffer_;
	}

	const std::uint8_t* getBuffer() const {
		return buffer_;
	}

private:
	bool append_scaled_2(std::uint8_t channel, std::uint8_t type, float value, float multiplier, bool is_signed) {
		if (length_ + 4 > max_size_) {
			return false;
		}
		buffer_[length_++] = channel;
		buffer_[length_++] = type;
		std::int32_t scaled = static_cast<std::int32_t>(value * multiplier);
		if (!is_signed && scaled < 0) {
			scaled = 0;
		}
		buffer_[length_++] = static_cast<std::uint8_t>((scaled >> 8) & 0xFF);
		buffer_[length_++] = static_cast<std::uint8_t>(scaled & 0xFF);
		return true;
	}

	bool append_uint16(std::uint8_t channel, std::uint8_t type, std::uint16_t value) {
		if (length_ + 4 > max_size_) {
			return false;
		}
		buffer_[length_++] = channel;
		buffer_[length_++] = type;
		buffer_[length_++] = static_cast<std::uint8_t>((value >> 8) & 0xFF);
		buffer_[length_++] = static_cast<std::uint8_t>(value & 0xFF);
		return true;
	}

	void append_int24(std::int32_t value) {
		buffer_[length_++] = static_cast<std::uint8_t>((value >> 16) & 0xFF);
		buffer_[length_++] = static_cast<std::uint8_t>((value >> 8) & 0xFF);
		buffer_[length_++] = static_cast<std::uint8_t>(value & 0xFF);
	}

	std::uint8_t buffer_[230];
	std::size_t length_;
	std::size_t max_size_;
};