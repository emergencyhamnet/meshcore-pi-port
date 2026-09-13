#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include <openssl/hmac.h>
#define SHA256 OpenSSL_SHA256
#include <openssl/sha.h>
#undef SHA256

class SHA256 {
public:
	SHA256()
		: hmac_ctx_(nullptr),
		  hmac_mode_(false) {
		reset();
	}

	~SHA256() {
		if (hmac_ctx_ != nullptr) {
			HMAC_CTX_free(hmac_ctx_);
		}
	}

	void update(const void* data, std::size_t length) {
		if (data == nullptr || length == 0) {
			return;
		}

		if (hmac_mode_) {
			HMAC_Update(hmac_ctx_, static_cast<const unsigned char*>(data), length);
		} else {
			::SHA256_Update(&sha_ctx_, data, length);
		}
	}

	void finalize(void* output, std::size_t output_length) {
		unsigned char digest[SHA256_DIGEST_LENGTH];
		::SHA256_Final(digest, &sha_ctx_);
		std::memcpy(output, digest, std::min(output_length, sizeof(digest)));
		reset();
	}

	void resetHMAC(const void* key, std::size_t length) {
		if (hmac_ctx_ == nullptr) {
			hmac_ctx_ = HMAC_CTX_new();
		}
		HMAC_CTX_reset(hmac_ctx_);
		HMAC_Init_ex(hmac_ctx_, key, static_cast<int>(length), EVP_sha256(), nullptr);
		hmac_mode_ = true;
	}

	void finalizeHMAC(const void*, std::size_t, void* output, std::size_t output_length) {
		unsigned char digest[EVP_MAX_MD_SIZE];
		unsigned int digest_length = 0;
		HMAC_Final(hmac_ctx_, digest, &digest_length);
		std::memcpy(output, digest, std::min<std::size_t>(output_length, digest_length));
		reset();
	}

private:
	void reset() {
		hmac_mode_ = false;
		::SHA256_Init(&sha_ctx_);
	}

	::SHA256_CTX sha_ctx_;
	HMAC_CTX* hmac_ctx_;
	bool hmac_mode_;
};