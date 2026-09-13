#pragma once

#include <cstddef>
#include <cstdint>

inline int decode_base64(const unsigned char* input, std::size_t length, unsigned char* output) {
	if (input == nullptr || output == nullptr) {
		return 0;
	}

	auto decode_char = [](unsigned char value) -> int {
		if (value >= 'A' && value <= 'Z') return value - 'A';
		if (value >= 'a' && value <= 'z') return value - 'a' + 26;
		if (value >= '0' && value <= '9') return value - '0' + 52;
		if (value == '+') return 62;
		if (value == '/') return 63;
		if (value == '=') return -2;
		return -1;
	};

	int output_length = 0;
	for (std::size_t index = 0; index < length;) {
		int sextets[4] = {0, 0, 0, 0};
		int padding = 0;
		for (int part = 0; part < 4 && index < length; ++part) {
			int decoded = decode_char(input[index++]);
			while (decoded == -1 && index < length) {
				decoded = decode_char(input[index++]);
			}
			if (decoded == -2) {
				decoded = 0;
				padding++;
			}
			sextets[part] = decoded < 0 ? 0 : decoded;
		}

		output[output_length++] = static_cast<unsigned char>((sextets[0] << 2) | (sextets[1] >> 4));
		if (padding < 2) {
			output[output_length++] = static_cast<unsigned char>(((sextets[1] & 0x0F) << 4) | (sextets[2] >> 2));
		}
		if (padding == 0) {
			output[output_length++] = static_cast<unsigned char>(((sextets[2] & 0x03) << 6) | sextets[3]);
		}
	}

	return output_length;
}