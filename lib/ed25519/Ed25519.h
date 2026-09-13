#pragma once

#include "ed_25519.h"

namespace Ed25519 {

inline bool verify(const unsigned char* signature,
				   const unsigned char* public_key,
				   const unsigned char* message,
				   size_t message_len) {
	return ed25519_verify(signature, message, message_len, public_key) != 0;
}

} // namespace Ed25519