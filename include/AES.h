#pragma once

#include <cstddef>
#include <cstdint>

#include <openssl/aes.h>

class AES128 {
public:
	AES128()
		: ready_(false) {}

	void setKey(const std::uint8_t* key, std::size_t length) {
		if (key == nullptr || length < 16) {
			ready_ = false;
			return;
		}

		AES_set_encrypt_key(key, 128, &encrypt_key_);
		AES_set_decrypt_key(key, 128, &decrypt_key_);
		ready_ = true;
	}

	void encryptBlock(std::uint8_t* output, const std::uint8_t* input) const {
		if (!ready_ || output == nullptr || input == nullptr) {
			return;
		}
		AES_encrypt(input, output, &encrypt_key_);
	}

	void decryptBlock(std::uint8_t* output, const std::uint8_t* input) const {
		if (!ready_ || output == nullptr || input == nullptr) {
			return;
		}
		AES_decrypt(input, output, &decrypt_key_);
	}

private:
	AES_KEY encrypt_key_;
	AES_KEY decrypt_key_;
	bool ready_;
};