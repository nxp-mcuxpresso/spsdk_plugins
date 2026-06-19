/*
 * Copyright 2024 NXP
 * All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef PRINCE_CORE
#define PRINCE_CORE

#include <stdint.h>
#include <string.h>
/**
 * The Round of the Prince cipher.
 */
uint64_t prince_round(const unsigned int nb_rounds, const uint64_t round_input, unsigned int round_index, const uint64_t k1);
/**
 * Top level function for Prince encryption/decryption.
 * enc_k0 and enc_k1 must be the same for encryption and decryption, the handling of decryption is done internally.
 */
uint64_t prince_enc_dec_uint64(const uint64_t input,
                               const uint64_t enc_k0, const uint64_t enc_k1,
                               int decrypt, const unsigned int nb_rounds,
                               int conf, uint64_t &half_enc_st,
                               uint64_t &half_dec_st);

/**
 * Byte oriented top level function for Prince encryption/decryption.
 * key_bytes 0 to 7 must contain K0
 * key_bytes 8 to 15 must contain K1
 */
void prince_enc_dec(const uint8_t in_bytes[8],
                    const uint8_t key_bytes[16],
                    uint8_t out_bytes[8], int decrypt,
                    const unsigned int nb_rounds, int conf,
                    uint8_t half_enc_st_bytes[8],
                    uint8_t half_dec_st_bytes[8]);
/**
 * Byte oriented top level function for Prince encryption.
 * key_bytes 0 to 7 must contain K0
 * key_bytes 8 to 15 must contain K1
 */
// void prince_encrypt(const uint8_t in_bytes[8],const uint8_t key_bytes[16], uint8_t out_bytes[8],unsigned int nb_rounds){
void prince_encrypt(const uint8_t in_bytes[8],
                    const uint8_t key_bytes[16],
                    unsigned int nb_rounds, int conf,
                    uint8_t out_bytes[8],
                    uint8_t half_enc_st_bytes[8],
                    uint8_t half_dec_st_bytes[8]);

/**
 * Byte oriented top level function for Prince decryption.
 * key_bytes 0 to 7 must contain K0
 * key_bytes 8 to 15 must contain K1
 */
// void prince_decrypt(const uint8_t in_bytes[8],const uint8_t key_bytes[16], uint8_t out_bytes[8],unsigned int nb_rounds){
void prince_decrypt(const uint8_t in_bytes[8],
                    const uint8_t key_bytes[16],
                    unsigned int nb_rounds, int conf,
                    uint8_t out_bytes[8],
                    uint8_t half_enc_st_bytes[8],
                    uint8_t half_dec_st_bytes[8]);

#endif
