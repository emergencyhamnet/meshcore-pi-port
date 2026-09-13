#pragma once

#include <cstdint>
#include <ctime>

class DateTime {
public:
	explicit DateTime(std::uint32_t epoch_seconds)
		: epoch_seconds_(static_cast<std::time_t>(epoch_seconds)) {}

	int hour() const { return utc_time().tm_hour; }
	int minute() const { return utc_time().tm_min; }
	int day() const { return utc_time().tm_mday; }
	int month() const { return utc_time().tm_mon + 1; }
	int year() const { return utc_time().tm_year + 1900; }

private:
	std::tm utc_time() const {
		std::tm result{};
#if defined(_WIN32)
		gmtime_s(&result, &epoch_seconds_);
#else
		gmtime_r(&epoch_seconds_, &result);
#endif
		return result;
	}

	std::time_t epoch_seconds_;
};