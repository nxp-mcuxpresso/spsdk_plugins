/*
 * Copyright 2024 NXP
 * All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef __EOS_REF_H__
#define __EOS_REF_H__

#include "PrinceCore.h"
// #define PRINCE_V2
#define ID_CFG_PRINCE_CORE_SBOX_VALUE_T0 0xBF32AC916780E5D4
#define ID_CFG_PRINCE_CORE_SBOX_VALUE_T1 0xBF32AC916780E5D4
#define ID_CFG_PRINCE_CORE_INV_SBOX_VALUE_T0 0xB732FD89A6405EC1
#define ID_CFG_PRINCE_CORE_INV_SBOX_VALUE_T1 0xB732FD89A6405EC1
// #define JWF_DEBUG

// #define TESTBENCH
// #define SOFT_TEST
#define EXEC

#ifdef TESTBENCH
#include "vpi_user.h"
#define PRINT(...) vpi_printf(__VA_ARGS__)
#elif defined EXEC
#include <cstdio>
#define PRINT(...) printf(__VA_ARGS__)
#elif defined SOFT_TEST
#include <stdio.h>
#define PRINT(...)
void *__gxx_personality_v0;
#endif

#ifndef UINT32_C
#define UINT32_C(c) (c##ULL)
#endif

#ifndef UINT64_C
#define UINT64_C(c) (c##ULL)
#endif

#ifndef PRINCE_PRINT
#define PRINCE_PRINT(a) \
    do                  \
    {                   \
    } while (0)
#endif

// #define ROUND_NUM 12

/**
 * Converts a byte array into a 32 bit integer
 * byte at index 0 is placed as the most significant byte.
 */
static uint32_t bytes_to_uint32(const uint8_t in[4])
{
    uint32_t out = 0;
    unsigned int i;
    for (i = 0; i < 4; i++)
        out = (out << 8) | in[i];
    return out;
}

static uint64_t bytes_to_uint64(const uint8_t in[8])
{
    uint64_t out = 0;
    unsigned int i;
    for (i = 0; i < 8; i++)
        out = (out << 8) | in[i];
    return out;
}
/**
 * Converts a 64 bit integer into a byte array
 * The most significant byte is placed at index 0.
 */
static void uint64_to_bytes(const uint64_t in, uint8_t out[8])
{
    unsigned int i;
    for (i = 0; i < 8; i++)
        out[i] = in >> ((7 - i) * 8);
}

/**
 * Converts a 32 bit integer into a byte array
 * The most significant byte is placed at index 0.
 */
static void uint32_to_bytes(const uint32_t in, uint8_t out[4])
{
    unsigned int i;
    for (i = 0; i < 4; i++)
        out[i] = in >> ((3 - i) * 8);
}

#define ALPHA_CONST 0xc0ac29b7c97c50dd
#define BETA_CONST 0x3f84d5b5b5470917
#ifdef TESTBENCH
extern "C" void prince_encrypt(const uint8_t in_bytes[8], const uint8_t key_bytes[16], unsigned int nb_rounds, uint8_t out_bytes[8]);
extern "C" void prince_decrypt(const uint8_t in_bytes[8], const uint8_t key_bytes[16], unsigned int nb_rounds, uint8_t out_bytes[8]);
#endif

/**
 * Compute K0' from K0
 */
static uint64_t prince_k0_to_k0_prime(const uint64_t k0)
{
    uint64_t k0_ror1 = (k0 >> 1) | (k0 << 63);
    uint64_t k0_prime = k0_ror1 ^ (k0 >> 63);
    return k0_prime;
}

static uint64_t prince_round_constant(const unsigned int round, const unsigned int nb_rounds)
{

#ifdef PRINCE_V2

    uint64_t rc[22];
    rc[0] = UINT64_C(0x0000000000000000);
    rc[1] = UINT64_C(0x13198a2e03707344);
    rc[2] = UINT64_C(0xa4093822299f31d0);
    rc[3] = UINT64_C(0x082efa98ec4e6c89);
    rc[4] = UINT64_C(0x452821e638d01377);
    rc[5] = UINT64_C(0xbe5466cf34e90c6c);
    for (unsigned int i = 6; i < 22; i++)
    {
        rc[i] = UINT64_C(0x0000000000000000);
    }

    for (unsigned int i = 0; i <= 5; i++)
    {
        rc[11 - i] = rc[i] ^ ((i % 2) ? ALPHA_CONST : BETA_CONST);
    }

    /*
    RC   generation  return on  return on
                     12 rounds  10 rounds
    ------------------------------------
    11     0 + b          11         -
    10     1 + a          10         9
     9     2 + b           9         8
     8     3 + a           8         7
     7     4 + b           7         6
     6     5 + a           6         5
     5     5               5         4
     4     4               4         3
     3     3               3         2
     2     2               2         1
     1     1               1         0
     0     0               0         -
    */

    return rc[round + 6 - (nb_rounds / 2)];

#else

    uint64_t rc[22];
    rc[0] = UINT64_C(0x0000000000000000);
    rc[1] = UINT64_C(0x13198a2e03707344);
    rc[2] = UINT64_C(0xa4093822299f31d0);
    if (nb_rounds > 6)
        rc[3] = UINT64_C(0x082efa98ec4e6c89);
    if (nb_rounds > 8)
        rc[4] = UINT64_C(0x452821e638d01377);
    if (nb_rounds > 10)
        rc[5] = UINT64_C(0xbe5466cf34e90c6c);
    if (nb_rounds > 12)
        rc[6] = UINT64_C(0x0f6d6ff383f44239);
    if (nb_rounds > 14)
        rc[7] = UINT64_C(0x1339b2eb3b52ec6f);
    if (nb_rounds > 16)
        rc[8] = UINT64_C(0x1a60320ad6a100c6);
    if (nb_rounds > 18)
        rc[9] = UINT64_C(0x8e7d44ec5716f2b8);
    if (nb_rounds > 20)
    {
        rc[10] = UINT64_C(0x214b7bf3d1f0cfc8);
    }

    for (unsigned int i = 0; i <= nb_rounds / 2 - 1; i = i + 1)
    {
        rc[nb_rounds - 1 - i] = rc[i] ^ ALPHA_CONST;
    }
    return rc[round];

#endif
}

/**
 * The 4 bit Prince sbox. Only the 4 lsb are takken into account.
 */
static unsigned int prince_sbox_t0(unsigned int nibble)
{
    uint8_t sb[8];
    uint8_t sbnibbles[16];
    uint64_to_bytes(ID_CFG_PRINCE_CORE_SBOX_VALUE_T0, sb);

    sbnibbles[0] = sb[0] >> 4;
    sbnibbles[1] = sb[0] & 0x0F;
    sbnibbles[2] = sb[1] >> 4;
    sbnibbles[3] = sb[1] & 0x0F;
    sbnibbles[4] = sb[2] >> 4;
    sbnibbles[5] = sb[2] & 0x0F;
    sbnibbles[6] = sb[3] >> 4;
    sbnibbles[7] = sb[3] & 0x0F;
    sbnibbles[8] = sb[4] >> 4;
    sbnibbles[9] = sb[4] & 0x0F;
    sbnibbles[10] = sb[5] >> 4;
    sbnibbles[11] = sb[5] & 0x0F;
    sbnibbles[12] = sb[6] >> 4;
    sbnibbles[13] = sb[6] & 0x0F;
    sbnibbles[14] = sb[7] >> 4;
    sbnibbles[15] = sb[7] & 0x0F;

    return sbnibbles[nibble & 0xF];
}
static unsigned int prince_sbox_t1(unsigned int nibble)
{
    uint8_t sb[8];
    uint8_t sbnibbles[16];
    uint64_to_bytes(ID_CFG_PRINCE_CORE_SBOX_VALUE_T1, sb);

    sbnibbles[0] = sb[0] >> 4;
    sbnibbles[1] = sb[0] & 0x0F;
    sbnibbles[2] = sb[1] >> 4;
    sbnibbles[3] = sb[1] & 0x0F;
    sbnibbles[4] = sb[2] >> 4;
    sbnibbles[5] = sb[2] & 0x0F;
    sbnibbles[6] = sb[3] >> 4;
    sbnibbles[7] = sb[3] & 0x0F;
    sbnibbles[8] = sb[4] >> 4;
    sbnibbles[9] = sb[4] & 0x0F;
    sbnibbles[10] = sb[5] >> 4;
    sbnibbles[11] = sb[5] & 0x0F;
    sbnibbles[12] = sb[6] >> 4;
    sbnibbles[13] = sb[6] & 0x0F;
    sbnibbles[14] = sb[7] >> 4;
    sbnibbles[15] = sb[7] & 0x0F;
    return sbnibbles[nibble & 0xF];
}
/**
 * The 4 bit Prince inverse sbox. Only the 4 lsb are takken into account.
 */
static unsigned int prince_sbox_inv_t0(unsigned int nibble)
{
    uint8_t sb[8];
    uint8_t sbnibbles[16];
    uint64_to_bytes(ID_CFG_PRINCE_CORE_INV_SBOX_VALUE_T0, sb);

    sbnibbles[0] = sb[0] >> 4;
    sbnibbles[1] = sb[0] & 0x0F;
    sbnibbles[2] = sb[1] >> 4;
    sbnibbles[3] = sb[1] & 0x0F;
    sbnibbles[4] = sb[2] >> 4;
    sbnibbles[5] = sb[2] & 0x0F;
    sbnibbles[6] = sb[3] >> 4;
    sbnibbles[7] = sb[3] & 0x0F;
    sbnibbles[8] = sb[4] >> 4;
    sbnibbles[9] = sb[4] & 0x0F;
    sbnibbles[10] = sb[5] >> 4;
    sbnibbles[11] = sb[5] & 0x0F;
    sbnibbles[12] = sb[6] >> 4;
    sbnibbles[13] = sb[6] & 0x0F;
    sbnibbles[14] = sb[7] >> 4;
    sbnibbles[15] = sb[7] & 0x0F;

    return sbnibbles[nibble & 0xF];
}

static unsigned int prince_sbox_inv_t1(unsigned int nibble)
{
    uint8_t sb[8];
    uint8_t sbnibbles[16];
    uint64_to_bytes(ID_CFG_PRINCE_CORE_INV_SBOX_VALUE_T1, sb);

    sbnibbles[0] = sb[0] >> 4;
    sbnibbles[1] = sb[0] & 0x0F;
    sbnibbles[2] = sb[1] >> 4;
    sbnibbles[3] = sb[1] & 0x0F;
    sbnibbles[4] = sb[2] >> 4;
    sbnibbles[5] = sb[2] & 0x0F;
    sbnibbles[6] = sb[3] >> 4;
    sbnibbles[7] = sb[3] & 0x0F;
    sbnibbles[8] = sb[4] >> 4;
    sbnibbles[9] = sb[4] & 0x0F;
    sbnibbles[10] = sb[5] >> 4;
    sbnibbles[11] = sb[5] & 0x0F;
    sbnibbles[12] = sb[6] >> 4;
    sbnibbles[13] = sb[6] & 0x0F;
    sbnibbles[14] = sb[7] >> 4;
    sbnibbles[15] = sb[7] & 0x0F;

    return sbnibbles[nibble & 0xF];
}
/**
 * The S step of the Prince cipher.
 */
static uint64_t prince_s_layer(const uint64_t s_in, unsigned int round_index)
{
    uint64_t s_out = 0;
    for (unsigned int i = 0; i < 16; i++)
    {
        const unsigned int shift = i * 4;
        const unsigned int sbox_in = s_in >> shift;
        uint64_t sbox_out;
        if ((round_index - 1) % 2 == 0)
        {
            sbox_out = prince_sbox_t0(sbox_in);
        }
        else
        {
            sbox_out = prince_sbox_t1(sbox_in);
        }
        s_out |= sbox_out << shift;
    }
    return s_out;
}

/**
 * The S^-1 step of the Prince cipher.
 */
static uint64_t prince_s_inv_layer(const uint64_t s_inv_in, unsigned int round_index)
{
    uint64_t s_inv_out = 0;
    for (unsigned int i = 0; i < 16; i++)
    {
        const unsigned int shift = i * 4;
        const unsigned int sbox_in = s_inv_in >> shift;
        uint64_t sbox_out;
        if ((round_index - 1) % 2 == 0)
        {
            sbox_out = prince_sbox_inv_t0(sbox_in);
        }
        else
        {
            sbox_out = prince_sbox_inv_t1(sbox_in);
        }
        s_inv_out |= sbox_out << shift;
    }
    return s_inv_out;
}

static uint64_t gf2_mat_mult16_1(const uint64_t in, const uint64_t mat[16])
{
    uint64_t out = 0;
    for (unsigned int i = 0; i < 16; i++)
    {
        if ((in >> i) & 1)
            out ^= mat[i];
    }
    return out;
}

/**
 * Build Prince's 16 bit matrices M0 and M1.
 */
static void prince_m16_matrices(uint64_t m16[2][16])
{
    // 4 bits matrices m0 to m3 are stored in array m4
    const uint64_t m4[4][4] = {
        // m0
        {0x0, 0x2, 0x4, 0x8},
        // m1
        {0x1, 0x0, 0x4, 0x8},
        // m2
        {0x1, 0x2, 0x0, 0x8},
        // m3
        {0x1, 0x2, 0x4, 0x0}};
    // build 16 bits matrices
    for (unsigned int i = 0; i < 16; i++)
    {
        const unsigned int base = i / 4;
        m16[0][i] = (m4[(base + 3) % 4][i % 4] << 8) | (m4[(base + 2) % 4][i % 4] << 4) | (m4[(base + 1) % 4][i % 4] << 0) | (m4[(base + 0) % 4][i % 4] << 12);
        m16[1][i] = (m16[0][i] >> 12) | (0xFFFF & (m16[0][i] << 4)); // m1 is just a rotated version of m0
    }
}

/**
 * The M' step of the Prince cipher.
 */
static uint64_t prince_m_prime_layer(const uint64_t m_prime_in)
{
    // 16 bits matrices M0 and M1, generated using the code below
    // uint64_t m16[2][16];prince_m16_matrices(m16);
    // for(unsigned int i=0;i<16;i++) PRINCE_PRINT(m16[0][i]);
    // for(unsigned int i=0;i<16;i++) PRINCE_PRINT(m16[1][i]);
    static const uint64_t m16[2][16] = {
        {0x0111,
         0x2220,
         0x4404,
         0x8088,
         0x1011,
         0x0222,
         0x4440,
         0x8808,
         0x1101,
         0x2022,
         0x0444,
         0x8880,
         0x1110,
         0x2202,
         0x4044,
         0x0888},

        {0x1110,
         0x2202,
         0x4044,
         0x0888,
         0x0111,
         0x2220,
         0x4404,
         0x8088,
         0x1011,
         0x0222,
         0x4440,
         0x8808,
         0x1101,
         0x2022,
         0x0444,
         0x8880}};
    const uint64_t chunk0 = gf2_mat_mult16_1(m_prime_in >> (0 * 16), m16[0]);
    const uint64_t chunk1 = gf2_mat_mult16_1(m_prime_in >> (1 * 16), m16[1]);
    const uint64_t chunk2 = gf2_mat_mult16_1(m_prime_in >> (2 * 16), m16[1]);
    const uint64_t chunk3 = gf2_mat_mult16_1(m_prime_in >> (3 * 16), m16[0]);
    const uint64_t m_prime_out = (chunk3 << (3 * 16)) | (chunk2 << (2 * 16)) | (chunk1 << (1 * 16)) | (chunk0 << (0 * 16));
    return m_prime_out;
}

/**
 * The shift row and inverse shift row of the Prince cipher.
 */
static uint64_t prince_shift_rows(const uint64_t in, int inverse)
{
    const uint64_t row_mask = UINT64_C(0xF000F000F000F000);
    uint64_t shift_rows_out = 0;
    for (unsigned int i = 0; i < 4; i++)
    {
        const uint64_t row = in & (row_mask >> (4 * i));
        const unsigned int shift = inverse ? i * 16 : 64 - i * 16;
        if (shift == 0 || shift == 64)
        {
            shift_rows_out |= row;
        }
        else
        {
            shift_rows_out |= (row >> shift) | (row << (64 - shift));
        }
    }
    return shift_rows_out;
}

/**
 * The M step of the Prince cipher.
 */
static uint64_t prince_m_layer(const uint64_t m_in)
{
    const uint64_t m_prime_out = prince_m_prime_layer(m_in);
    const uint64_t shift_rows_out = prince_shift_rows(m_prime_out, 0);
    return shift_rows_out;
}

/**
 * The M^-1 step of the Prince cipher.
 */
static uint64_t prince_m_inv_layer(const uint64_t m_inv_in)
{
    const uint64_t shift_rows_out = prince_shift_rows(m_inv_in, 1);
    const uint64_t m_prime_out = prince_m_prime_layer(shift_rows_out);
    return m_prime_out;
}
/**
 * The Round of the Prince cipher.
 */
uint64_t prince_round(const unsigned int nb_rounds, const uint64_t round_input, unsigned int round_index, const uint64_t k1)
{
    uint64_t round_out = 0;
    const uint64_t s_out = prince_s_layer(round_input, round_index);
    const uint64_t m_out = prince_m_layer(s_out);

    round_out = m_out ^ k1 ^ prince_round_constant(round_index, nb_rounds);

    return round_out;
}

/**
 * The core function of the Prince cipher.
 */
static uint64_t prince_core(const uint64_t core_input,
#ifdef PRINCE_V2
                            uint64_t k0, const int decrypt,
#endif
                            uint64_t k1, const unsigned int nb_rounds,
                            int conf, uint64_t &half_enc_st, uint64_t &half_dec_st)
{
    PRINCE_PRINT(core_input);
#ifdef PRINCE_V2
    PRINCE_PRINT(k0);
#endif
    PRINCE_PRINT(k1);
#ifdef JWF_DEBUG
#ifdef PRINCE_V2
    PRINT("jjj: k0 0x%llx\n", k0);
    PRINT("gmc: nb_rounds %d\n", nb_rounds);
#endif
    PRINT("jjj: k1 0x%llx\n", k1);
    PRINT("jjj: core input after whitening 0x%llx\n", core_input);
#endif
#ifdef PRINCE_V2
    uint64_t round_input = core_input ^ prince_round_constant(0, nb_rounds);
#else
    uint64_t round_input = core_input ^ k1 ^ prince_round_constant(0, nb_rounds);
#endif
    int round_index;
    int nb_rounds_eff = (conf != 0) ? nb_rounds * (conf + 1) - 2 : nb_rounds;
    for (unsigned int round = 1; round < nb_rounds_eff / 2; round++)
    {
#ifdef JWF_DEBUG
        PRINT("jjj: round %d input 0x%llx\n", round, round_input);
#endif
        PRINCE_PRINT(round_input);
        if (round < nb_rounds / 2)
        {
            round_index = round;
        }
        else
        {
            round_index = round - (nb_rounds / 2 - 1);
        }
        const uint64_t s_out = prince_s_layer(round_input, round_index);
#ifdef JWF_DEBUG
        PRINT("jjj: after s 0x%llx\n", s_out);
#endif
        PRINCE_PRINT(s_out);
        const uint64_t m_out = prince_m_layer(s_out);
#ifdef JWF_DEBUG
        PRINT("jjj: after m 0x%llx\n", m_out);
#endif
        PRINCE_PRINT(m_out);
#ifdef PRINCE_V2
        uint64_t k = (nb_rounds % 4) ? ((round % 2) ? k0 : k1)
                                     : ((round % 2) ? k1 : k0);
        round_input = m_out ^ k ^ prince_round_constant(round, nb_rounds_eff);
#ifdef JWF_DEBUG
        int kn = (nb_rounds % 4) ? ((round % 2) ? 0 : 1)
                                 : ((round % 2) ? 1 : 0);
        PRINT("jjj: xor k%0d 0x%llx xor rc 0x%llx result 0x%llx\n",
              kn, k, prince_round_constant(round, nb_rounds_eff), round_input);
#endif
#else
        round_input = m_out ^ k1 ^ prince_round_constant(round, nb_rounds_eff);
#endif
    }
#ifdef JWF_DEBUG
    PRINT("jjj: middle round input 0x%llx\n", round_input);
#endif
    uint64_t middle_round_s_out = prince_s_layer(round_input, 2);
    PRINCE_PRINT(middle_round_s_out);
    half_enc_st = middle_round_s_out;
#ifdef JWF_DEBUG
    PRINT("jjj: middle round after s layer 0x%llx\n", middle_round_s_out);
#endif
#ifdef PRINCE_V2
    middle_round_s_out ^= k0;
#ifdef JWF_DEBUG
    PRINT("jjj: middle round after xor  k0 0x%llx result 0x%llx\n", k0, middle_round_s_out);
#endif
#endif
    uint64_t m_prime_out = prince_m_prime_layer(middle_round_s_out);
    half_dec_st = m_prime_out;
    PRINCE_PRINT(m_prime_out);
#ifdef JWF_DEBUG
    PRINT("jjj: middle round after m layer 0x%llx\n", m_prime_out);
#endif
#ifdef PRINCE_V2
    if (decrypt)
    {
        k0 ^= ALPHA_CONST ^ BETA_CONST;
        k1 ^= ALPHA_CONST ^ BETA_CONST;
#ifdef JWF_DEBUG
        PRINT("jjj: decrypt xored both keys with both constants\n");
        PRINT("jjj: k0 is 0x%llx\n", k0);
        PRINT("jjj: k1 is 0x%llx\n", k1);
#endif
    }
    m_prime_out ^= k1 ^ BETA_CONST;
#ifdef JWF_DEBUG
    PRINT("jjj: middle round after xor k1 0x%llx xor beta 0x%llx result 0x%llx\n",
          k1, BETA_CONST, m_prime_out);
#endif
#endif
    const uint64_t middle_round_s_inv_out = prince_s_inv_layer(m_prime_out, 2);
#ifdef JWF_DEBUG
    PRINT("jjj: middle round after s_inv 0x%llx\n", middle_round_s_inv_out);
#endif
    round_input = middle_round_s_inv_out;

    for (unsigned int round = nb_rounds_eff / 2 + 2; round < nb_rounds_eff + 1; round++)
    {
#ifdef JWF_DEBUG
        PRINT("jjj: round %d input 0x%llx\n", round, round_input);
#endif
        PRINCE_PRINT(round_input);
        if (round < nb_rounds_eff / 2 + nb_rounds / 2 + 1)
        {
            round_index = (conf != 0) ? round - 2 : round - 1;
        }
        else
        {
            round_index = round - nb_rounds / 2 + 1;
        }
#ifdef PRINCE_V2
        uint64_t k = (nb_rounds % 4) ? ((round % 2) ? k0 : k1)
                                     : ((round % 2) ? k1 : k0);
        const uint64_t m_inv_in = round_input ^ k ^
                                  prince_round_constant(round - 2, nb_rounds_eff);
#ifdef JWF_DEBUG
        int kn = (nb_rounds % 4) ? ((round % 2) ? 0 : 1)
                                 : ((round % 2) ? 1 : 0);
        PRINT("jjj: xor k%0d 0x%llx xor RC 0x%llx result 0x%llx\n",
              kn, k, prince_round_constant(round - 2, nb_rounds_eff), m_inv_in);
#endif
#else
        const uint64_t m_inv_in = round_input ^ k1 ^ prince_round_constant(round - 2, nb_rounds_eff);
#endif
        PRINCE_PRINT(m_inv_in);
        const uint64_t s_inv_in = prince_m_inv_layer(m_inv_in);
#ifdef JWF_DEBUG
        PRINT("jjj: after m_inv 0x%llx\n", s_inv_in);
#endif
        PRINCE_PRINT(s_inv_in);
        const uint64_t s_inv_out = prince_s_inv_layer(s_inv_in, nb_rounds_eff - round_index);
        round_input = s_inv_out;
#ifdef JWF_DEBUG
        PRINT("jjj: after s_inv 0x%llx\n", s_inv_out);
#endif
    }
#ifdef SOFT_TEST
#ifdef PRINCE_V2
    PRINT("jjj: end of rounds 0x%llx\n", round_input);
#endif
#endif
#ifdef PRINCE_V2
    uint64_t k = (nb_rounds % 4) ? k0 : k1;
    uint64_t c = decrypt ? ((nb_rounds % 4) ? ALPHA_CONST : BETA_CONST)
                         : BETA_CONST;
    uint64_t core_output = round_input ^ k ^ prince_round_constant(nb_rounds_eff - 1, nb_rounds_eff);
#ifdef JWF_DEBUG
    int kn = (nb_rounds % 4) ? 0 : 1;
    char cn = decrypt ? ((nb_rounds % 4) ? 'a' : 'b') : 'b';
    PRINT("jjj: xor k%0d 0x%llx xor %s 0x%llx xor rc 0x%llx core_output 0x%llx\n",
          kn, k, (cn == 'a') ? "ALPHA" : "BETA", c,
          prince_round_constant(nb_rounds_eff - 1, nb_rounds_eff), core_output);
#endif
#else
    const uint64_t core_output = round_input ^ k1 ^ prince_round_constant(nb_rounds_eff - 1, nb_rounds_eff);
#endif
    PRINCE_PRINT(core_output);
    return core_output;
}

/**
 * Top level function for Prince encryption/decryption.
 * enc_k0 and enc_k1 must be the same for encryption and decryption, the handling of decryption is done internally.
 */
uint64_t prince_enc_dec_uint64(const uint64_t input, const uint64_t enc_k0, const uint64_t enc_k1,
                               int decrypt, const unsigned int nb_rounds, int conf, uint64_t &half_enc_st,
                               uint64_t &half_dec_st)
{

#ifdef SOFT_TEST
    PRINT("jjj: data 0x%llx, k0 0x%llx, k1 0x%llx, dec %d\n", input, enc_k0, enc_k1, decrypt);
    PRINT("jjj: nb_rounds %d, conf %d\n", nb_rounds, conf);
#endif

#ifdef PRINCE_V2
    const uint64_t k0 = decrypt ? (enc_k1 ^ BETA_CONST) : enc_k0;
    const uint64_t k1 = decrypt ? (enc_k0 ^ ALPHA_CONST) : enc_k1;
#else
    const uint64_t k1 = enc_k1 ^ (decrypt ? ALPHA_CONST : 0);
    const uint64_t enc_k0_prime = prince_k0_to_k0_prime(enc_k0);
    const uint64_t k0 = decrypt ? enc_k0_prime : enc_k0;
    const uint64_t k0_prime = decrypt ? enc_k0 : enc_k0_prime;
#endif
    // uint64_t *half_enc_temp, *half_dec_temp;
    PRINCE_PRINT(k0);
    PRINCE_PRINT(input);
#ifdef PRINCE_V2
#ifdef JWF_DEBUG
    PRINT("gmc: input before whitening 0x%llx\n", input);
#endif
    const uint64_t core_input = input ^ ((nb_rounds % 4) ? k1 : k0);
#else
    const uint64_t core_input = input ^ k0;
#endif
    const uint64_t core_output = prince_core(core_input,
#ifdef PRINCE_V2
                                             k0, decrypt,
#endif
                                             k1, nb_rounds, conf, half_enc_st, half_dec_st);
    const uint64_t output = core_output
#ifndef PRINCE_V2
                            ^ k0_prime
#endif
        ;
    // half_enc_st = half_enc_temp;
    // half_dec_st = half_dec_temp;
#ifndef PRINCE_V2
    PRINCE_PRINT(k0_prime);
#endif
    PRINCE_PRINT(output);

#ifdef SOFT_TEST
    PRINT("jjj: result 0x%llx\n", output);
#endif
    return output;
}

/**
 * Byte oriented top level function for Prince encryption/decryption.
 * key_bytes 0 to 7 must contain K0
 * key_bytes 8 to 15 must contain K1
 */
void prince_enc_dec(const uint8_t in_bytes[8], const uint8_t key_bytes[16], uint8_t out_bytes[8],
                    int decrypt, const unsigned int nb_rounds, int conf, uint8_t half_enc_st_bytes[8],
                    uint8_t half_dec_st_bytes[8])
{
    const uint64_t input = bytes_to_uint64(in_bytes);
    const uint64_t enc_k0 = bytes_to_uint64(key_bytes);
    const uint64_t enc_k1 = bytes_to_uint64(key_bytes + 8);
    uint64_t half_enc_st;
    uint64_t half_dec_st;
    const uint64_t output = prince_enc_dec_uint64(input, enc_k0, enc_k1, decrypt, nb_rounds,
                                                  conf, half_enc_st, half_dec_st);
    uint64_to_bytes(output, out_bytes);
    uint64_to_bytes(half_enc_st, half_enc_st_bytes);
    uint64_to_bytes(half_dec_st, half_dec_st_bytes);
}

/**
 * Byte oriented top level function for Prince encryption.
 * key_bytes 0 to 7 must contain K0
 * key_bytes 8 to 15 must contain K1
 */
void prince_encrypt(const uint8_t in_bytes[8], const uint8_t key_bytes[16], unsigned int nb_rounds,
                    uint8_t out_bytes[8], int conf, uint8_t half_enc_st_bytes[8], uint8_t half_dec_st_bytes[8])
{
    prince_enc_dec(in_bytes, key_bytes, out_bytes, 0, nb_rounds, conf, half_enc_st_bytes,
                   half_dec_st_bytes);
}

/**
 * Byte oriented top level function for Prince decryption.
 * key_bytes 0 to 7 must contain K0
 * key_bytes 8 to 15 must contain K1
 */
void prince_decrypt(const uint8_t in_bytes[8], const uint8_t key_bytes[16], unsigned int nb_rounds,
                    uint8_t out_bytes[8], int conf, uint8_t half_enc_st_bytes[8], uint8_t half_dec_st_bytes[8])
{
    prince_enc_dec(in_bytes, key_bytes, out_bytes, 1, nb_rounds, conf, half_enc_st_bytes,
                   half_dec_st_bytes);
}

#ifdef SOFT_TEST

int main(int argc, char *argv[])
{
    PRINT("stand alone wrapper\n");

#define N 4
    uint64_t inp[N];
    uint64_t k0[N];
    uint64_t k1[N];
    uint64_t kat[N];

    inp[0] = 0xabcdabcdabcdabcd;
    k0[0] = 0x1234123412341234;
    k1[0] = 0x5678567856785678;
#ifdef PRINCE_V2
    kat[0] = 0x854fa71a155f93e8;
#else
    kat[0] = 0xb29aa649a2244361;
#endif

    inp[1] = 0x1234567890abcdef;
    k0[1] = 0x1234567890abcdef;
    k1[1] = 0x1234567890abcdef;
#ifdef PRINCE_V2
    kat[1] = 0x17ae407dec9bf277;
#else
    kat[1] = 0xb874717db3bd9ab7;
#endif

    inp[2] = 0x5745c17a7734770b;
    k0[2] = 0x0000000000000000;
    k1[2] = 0x0000000000000000;
#ifdef PRINCE_V2
    kat[2] = 0xfeb262b4fee5381b;
#else
    kat[2] = 0xff5597e7b8a4169c;
#endif

    inp[3] = 0x5743266545635673;
    k0[3] = 0x4313325662442565;
    k1[3] = 0x5235675624565456;
#ifdef PRINCE_V2
    kat[3] = 0x0899406fe33f7e2c;
#else
    kat[3] = 0x6828dc2a2f2bdd8d;
#endif

#ifdef PRINCE_V2
#define VENTZI_N 35

    uint64_t ventzi_inp[VENTZI_N];
    uint64_t ventzi_k0[VENTZI_N];
    uint64_t ventzi_k1[VENTZI_N];
    uint64_t ventzi_kat[VENTZI_N];
    uint64_t ventzi_rounds[VENTZI_N];

    int i = 0;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0x3e1eec758e6eb76e;
    ventzi_kat[i] = 0xa258dc467d4c020d;
    ventzi_rounds[i++] = 4;

    ventzi_k0[i] = 0xffffffffffffffff;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0x6fbedf7581ea6caf;
    ventzi_kat[i] = 0x0a0490758ddb28fb;
    ventzi_rounds[i++] = 4;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0xffffffffffffffff;
    ventzi_inp[i] = 0x5505d4e64fb02010;
    ventzi_kat[i] = 0x91cceb6e87fb73fa;
    ventzi_rounds[i++] = 4;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0x63b6ba98add6835b;
    ventzi_kat[i] = 0xd73c8674138ef51c;
    ventzi_rounds[i++] = 4;

    ventzi_k0[i] = 0x0123456789abcdef;
    ventzi_k1[i] = 0xfedcba9876543210;
    ventzi_inp[i] = 0x2f2b50c2d0a59fa0;
    ventzi_kat[i] = 0x9525399d08611e16;
    ventzi_rounds[i++] = 4;

    ventzi_k0[i] = 0x117542907c0b9db6;
    ventzi_k1[i] = 0x4c1d1c6a025886e9;
    ventzi_inp[i] = 0x3b561125fabeb86c;
    ventzi_kat[i] = 0x2f0d4fd16dd9549e;
    ventzi_rounds[i++] = 4;

    ventzi_k0[i] = 0x76229819de676b27;
    ventzi_k1[i] = 0x3ee0a022d5340c73;
    ventzi_inp[i] = 0x2f32893bae21704a;
    ventzi_kat[i] = 0xff00d47856c48812;
    ventzi_rounds[i++] = 4;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0xb59d7610dd3755cb;
    ventzi_kat[i] = 0xf2d73a1fe8faeaea;
    ventzi_rounds[i++] = 6;

    ventzi_k0[i] = 0xffffffffffffffff;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0x8530aafd402b3ee3;
    ventzi_kat[i] = 0x40287d75d8b98da0;
    ventzi_rounds[i++] = 6;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0xffffffffffffffff;
    ventzi_inp[i] = 0xb9215fcae80eec12;
    ventzi_kat[i] = 0xb30758c4303c63b5;
    ventzi_rounds[i++] = 6;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0xb9215fcae80eec12;
    ventzi_kat[i] = 0x63efde1a005ed6e7;
    ventzi_rounds[i++] = 6;

    ventzi_k0[i] = 0x0123456789abcdef;
    ventzi_k1[i] = 0xfedcba9876543210;
    ventzi_inp[i] = 0xdf336a539bd7c61f;
    ventzi_kat[i] = 0xe1060bda46080ede;
    ventzi_rounds[i++] = 6;

    ventzi_k0[i] = 0x1e070772e4e853b8;
    ventzi_k1[i] = 0x98a5d5f8bc03dd46;
    ventzi_inp[i] = 0x1d8d2401fb66994d;
    ventzi_kat[i] = 0x71f5f82645eceacb;
    ventzi_rounds[i++] = 6;

    ventzi_k0[i] = 0x6ae4356b4eb16428;
    ventzi_k1[i] = 0x8975a66ad857ffdd;
    ventzi_inp[i] = 0x1ede0274886efa18;
    ventzi_kat[i] = 0xcc64a5800f30358a;
    ventzi_rounds[i++] = 6;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0x81ccd0e7aed047ae;
    ventzi_kat[i] = 0x5f89fcaeca385543;
    ventzi_rounds[i++] = 8;

    ventzi_k0[i] = 0xffffffffffffffff;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0xd911f080ba9e00a9;
    ventzi_kat[i] = 0x28cc414e1edde0d5;
    ventzi_rounds[i++] = 8;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0xffffffffffffffff;
    ventzi_inp[i] = 0xd911f080ba9e00a9;
    ventzi_kat[i] = 0xb1ded7daa9b69118;
    ventzi_rounds[i++] = 8;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0xd911f080ba9e00a9;
    ventzi_kat[i] = 0x906b5ff84cb3745c;
    ventzi_rounds[i++] = 8;

    ventzi_k0[i] = 0x0123456789abcdef;
    ventzi_k1[i] = 0xfedcba9876543210;
    ventzi_inp[i] = 0x06c9d79150cb548e;
    ventzi_kat[i] = 0xeafab9b0f58b66a7;
    ventzi_rounds[i++] = 8;

    ventzi_k0[i] = 0x6d678ca1fed0581c;
    ventzi_k1[i] = 0x0307cddd4d75cc29;
    ventzi_inp[i] = 0x0f0e8d6811984d78;
    ventzi_kat[i] = 0xf847f2faed95234c;
    ventzi_rounds[i++] = 8;

    ventzi_k0[i] = 0x8f8580f4c8fc04af;
    ventzi_k1[i] = 0x6a97e8d2175e98dd;
    ventzi_inp[i] = 0x372fc8b91ea8c023;
    ventzi_kat[i] = 0xa2c3ad144be1ff3e;
    ventzi_rounds[i++] = 8;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0xbbbbbbbbbbbbbbbb;
    ventzi_kat[i] = 0xd81992e2d8743064;
    ventzi_rounds[i++] = 10;

    ventzi_k0[i] = 0xffffffffffffffff;
    ventzi_k1[i] = 0x0000000000000000;
    UINT64_C(0x452821e638d01377);
    ventzi_inp[i] = 0x4444444444444444;
    ventzi_kat[i] = 0x565327d85aa924a9;
    ventzi_rounds[i++] = 10;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0xffffffffffffffff;
    ventzi_inp[i] = 0xbbbbbbbbbbbbbbbb;
    ventzi_kat[i] = 0xa00f6f3be853275c;
    ventzi_rounds[i++] = 10;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0x4444444444444444;
    ventzi_kat[i] = 0x6a34216ad5e58042;
    ventzi_rounds[i++] = 10;

    ventzi_k0[i] = 0x0123456789abcdef;
    ventzi_k1[i] = 0xfedcba9876543210;
    ventzi_inp[i] = 0xbbbbbbbbbbbbbbbb;
    ventzi_kat[i] = 0x8adda2fe44da1f1d;
    ventzi_rounds[i++] = 10;

    ventzi_k0[i] = 0xc49537e585c24c0d;
    ventzi_k1[i] = 0x415718a8f7ad7383;
    ventzi_inp[i] = 0x0ff043d3be97afaf;
    ventzi_kat[i] = 0xcbe5127d8f043236;
    ventzi_rounds[i++] = 10;

    ventzi_k0[i] = 0x6867c2af5b963c4e;
    ventzi_k1[i] = 0xa083c20009163b9f;
    ventzi_inp[i] = 0x51c63c64fee000ee;
    ventzi_kat[i] = 0xd77c54b8e55cb9dc;
    ventzi_rounds[i++] = 10;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0x0000000000000000;
    ventzi_kat[i] = 0x0125fc7359441690;
    ventzi_rounds[i++] = 12;

    ventzi_k0[i] = 0xffffffffffffffff;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0x0000000000000000;
    ventzi_kat[i] = 0xee873b2ec447944d;
    ventzi_rounds[i++] = 12;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0xffffffffffffffff;
    ventzi_inp[i] = 0x0000000000000000;
    ventzi_kat[i] = 0x0ac6f9cd6e6f275d;
    ventzi_rounds[i++] = 12;

    ventzi_k0[i] = 0x0000000000000000;
    ventzi_k1[i] = 0x0000000000000000;
    ventzi_inp[i] = 0xffffffffffffffff;
    ventzi_kat[i] = 0x832bd46f108e7857;
    ventzi_rounds[i++] = 12;

    ventzi_k0[i] = 0x0123456789abcdef;
    ventzi_k1[i] = 0xfedcba9876543210;
    ventzi_inp[i] = 0x0123456789abcdef;
    ventzi_kat[i] = 0x603cd95fa72a8704;
    ventzi_rounds[i++] = 12;

    ventzi_k0[i] = 0xbf1c3f78d696c90c;
    ventzi_k1[i] = 0xa2594d9bf753097e;
    ventzi_inp[i] = 0xf2ab9d90c6dbb113;
    ventzi_kat[i] = 0x1adfa4244abb735f;
    ventzi_rounds[i++] = 12;

    ventzi_k0[i] = 0x876f6fd821b0d2bf;
    ventzi_k1[i] = 0x3083a830d5088811;
    ventzi_inp[i] = 0x6b2757c3ad9981d6;
    ventzi_kat[i] = 0x7b3709b5562504a2;
    ventzi_rounds[i++] = 12;
#endif

    uint64_t t1, t2;

    for (int i = 0; i < N; i++)
    {
        uint64_t outp = prince_enc_dec_uint64(inp[i], k0[i], k1[i], 0, 12, 0, t1, t2);
        if (outp == kat[i])
        {
            PRINT("PASS test %d encryption!\n", i);
        }
        else
        {
            PRINT("FAIL test %d encryption! (output 0x%llx expected 0x%llx)\n", i, outp, kat[i]);
        }
        outp = prince_enc_dec_uint64(kat[i], k0[i], k1[i], 1, 12, 0, t1, t2);
        if (outp == inp[i])
        {
            PRINT("PASS test %d decryption!\n", i);
        }
        else
        {
            PRINT("FAIL test %d decryption! (output 0x%llx expected 0x%llx)\n", i, outp, inp[i]);
        }
    }
    for (int i = 0; i < N; i++)
    {
        uint64_t cypher = prince_enc_dec_uint64(inp[i], k0[i], k1[i], 0, 10, 0, t1, t2);
        uint64_t plain = prince_enc_dec_uint64(cypher, k0[i], k1[i], 1, 10, 0, t1, t2);
        if (inp[i] == plain)
        {
            PRINT("PASS test %d encryption/decryption sequence for 10 rounds!\n", i);
        }
        else
        {
            PRINT("FAIL test %d encryption/decryption sequence for 10 rounds!\n", i);
            PRINT("  (plain in 0x%llx cypher 0x%llx plain_out 0x%llx)\n", inp[i], cypher, plain);
        }
    }
#ifdef PRINCE_V2
    for (int i = 0; i < VENTZI_N; i++)
    {
        uint64_t cypher = prince_enc_dec_uint64(ventzi_inp[i], ventzi_k0[i], ventzi_k1[i],
                                                0, ventzi_rounds[i], 0, t1, t2);
        uint64_t plain = prince_enc_dec_uint64(ventzi_kat[i], ventzi_k0[i], ventzi_k1[i],
                                               1, ventzi_rounds[i], 0, t1, t2);
        if (ventzi_kat[i] == cypher)
        {
            PRINT("PASS test ventzi_%0d encryption!\n", i);
        }
        else
        {
            PRINT("FAIL test ventzi_%0d encryption!\n", i);
        }
        if (ventzi_inp[i] == plain)
        {
            PRINT("PASS test ventzi_%0d decryption!\n", i);
        }
        else
        {
            PRINT("FAIL test ventzi_%0d decryption!\n", i);
        }
    }
#endif
}

#endif
#endif //__EOS_REF_H__
