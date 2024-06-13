#ifndef SIGN_H
#define SIGN_H

#include <stddef.h>
#include <stdint.h>
#include "params.h"
#include "polyvec.h"
#include "poly.h"

#if defined(_WIN32)
#define DIL_EXPORT_API __declspec(dllexport)
#else
#define DIL_EXPORT_API
#endif

#define challenge DILITHIUM_NAMESPACE(challenge)
DIL_EXPORT_API void challenge(poly *c, const uint8_t seed[SEEDBYTES]);

#define crypto_sign_keypair DILITHIUM_NAMESPACE(keypair)
DIL_EXPORT_API int crypto_sign_keypair(uint8_t *pk, uint8_t *sk);

#define crypto_sign_signature DILITHIUM_NAMESPACE(signature)
DIL_EXPORT_API int crypto_sign_signature(uint8_t *sig, size_t *siglen,
                                         const uint8_t *m, size_t mlen,
                                         const uint8_t *sk);

#define crypto_sign DILITHIUM_NAMESPACETOP
DIL_EXPORT_API int crypto_sign(uint8_t *sm, size_t *smlen,
                               const uint8_t *m, size_t mlen,
                               const uint8_t *sk);

#define crypto_sign_verify DILITHIUM_NAMESPACE(verify)
DIL_EXPORT_API int crypto_sign_verify(const uint8_t *sig, size_t siglen,
                                      const uint8_t *m, size_t mlen,
                                      const uint8_t *pk);

#define crypto_sign_open DILITHIUM_NAMESPACE(open)
DIL_EXPORT_API int crypto_sign_open(uint8_t *m, size_t *mlen,
                                    const uint8_t *sm, size_t smlen,
                                    const uint8_t *pk);

#endif
