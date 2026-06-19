/*
 * Copyright 2024 NXP
 * All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef __EOS_REF_H__
#define __EOS_REF_H__

// #define JWF_DEBUG

// #define TESTBENCH
// #define SOFT_TEST
#define EXEC

#ifdef JWF_DEBUG
#ifdef TESTBENCH
#include <stdint.h>
#include <string.h>
#include "vpi_user.h"
#define PRINT(...) vpi_printf(__VA_ARGS__)
#elif defined EXEC
#include <cstdio>
#define PRINT(...) printf(__VA_ARGS__)
#elif defined SOFT_TEST
#define PRINT(...)
#endif
#else
#define PRINT(...)
#endif

#ifndef UINT32_C
#define UINT32_C(c) (c##ULL)
#endif

#ifndef UINT64_C
#define UINT64_C(c) (c##ULL)
#endif

#define DATA_MAX 4

#ifdef EXEC
#include "ip_prince_ctr.h"
#include "PrinceCore.h"
#elif defined TESTBENCH
enum state_t
{
    IDLE = 1,
    GCM_H_ENC = 2,
    GCM_CTR0_ENC = 4,
    GCM_CTRN_ENC = 8,
    GCM_LAST_DGHASH = 16,
    GCM_TAG_DONE = 32,
    CTR_ENC_MODE = 64
};
#include "../submodules/ip_prince/ALGORITHM/PrinceCore.h"
extern "C" void ctr_prince_mem_enc(const int debug, const unsigned int data_nb_rounds, int conf, int mode, uint64_t in_data, const uint64_t in_iv, const uint64_t in_address, const uint64_t data_key0, const uint64_t data_key1, uint64_t &o_data);
// cextern "C" uint64_t ghash_mul(  uint64_t x_op,  uint64_t y_op);
extern "C" void gcm_prince_mem_enc_steps(const int debug, const unsigned int data_nb_rounds, int conf, int mode, int prince_state, const uint64_t in_data, const uint64_t in_iv, const uint64_t in_address, const uint64_t data_key0, const uint64_t data_key1, const uint64_t in_ad, const uint64_t prev_tag, const uint64_t prev_data, const uint64_t h_op, const uint64_t ctr0_op, const uint64_t len_a_c, uint64_t &o_data, uint64_t &o_auth_tag);
extern "C" void gcm_prince_mem_enc(const int debug, const unsigned int data_nb_rounds, const unsigned int block_num, int conf, int mode, int dec, uint64_t in_data[], const uint64_t in_iv, uint64_t in_address[], const uint64_t data_key0, const uint64_t data_key1, const uint64_t in_ad, uint64_t o_data[], uint64_t &o_auth_tag);
#elif defined SOFT_TEST
#include "../submodules/ip_prince/ALGORITHM/PrinceCore.h"
#endif

/* PLAIN CTR PRINCE FUNCTION */
void ctr_prince_mem_enc(const int debug,
                        const unsigned int data_nb_rounds,
                        int conf,
                        int mode,
                        const uint64_t in_data,
                        const uint64_t in_iv,
                        const uint64_t in_address,
                        const uint64_t data_key0, const uint64_t data_key1,
                        uint64_t &o_data)
{

    uint64_t half_enc_st, half_dec_st;
    const uint32_t address_const = 0x67696F66;
    uint64_t sh_address = (in_address) << 32;                                                        // Shifting left to remove the first 32 bit not used by Prince
    uint64_t expanded_address = (~in_address ^ mode) << 32 | (((sh_address >> 32) ^ address_const)); // Shifting again right to get back the original 32LSBs
                                                                                                     // Round 0 CTR mode//
    PRINT("Debug = %d, data_nb_rounds = %d, conf=%d, mode=%d, in_data=%llx, in_iv=%llx, in_address=%llx, data_key0=%llx, data_key1=%llx\n", debug, data_nb_rounds, conf, mode, in_data, in_iv, in_address, data_key0, data_key1);
    PRINT("mode=%d, data_nb_rounds=%d, Address =%llx,shifted_address =%llx, expanded_address =%llx , i_iv=%llx \n", mode, data_nb_rounds, in_address, sh_address, expanded_address, in_iv);
    const uint64_t prince_in = prince_round(12, expanded_address, 1, in_iv);
    PRINT(" Prince_in =%llx , data_key0=%llx, data_key1=%llx, conf=%d \n", prince_in, data_key0, data_key1, conf);
    const uint64_t prince_out = prince_enc_dec_uint64(prince_in, data_key0, data_key1, 0, data_nb_rounds, conf, half_enc_st, half_dec_st);
    PRINT("in_data:%llx \n", in_data);
    o_data = prince_out ^ in_data;
    PRINT(" Prince_out =%llx, o_data=%llx \n", prince_out, o_data);
}

/* GHASHE FUNCTION */
uint64_t ghash_mul(uint64_t x_op,
                   uint64_t y_op)
{
    uint64_t x_next, z_next;
    const uint64_t R_const = 0x1B;

    x_next = x_op;
    z_next = 0;

    for (int i = 0; i < 64; i++)
    {
        z_next = ((y_op >> i) & 0x1) ? z_next ^ x_next : z_next;
        x_next = ((x_next >> 63) & 0x1) ? (x_next << 1) ^ R_const : (x_next << 1);
        // printf(" Z_next=%016llx, X_next=%016llx stage %d \n", z_next, x_next, i);
    }
    //     PRINT("GHASH: Inputs X=%016llx Y=%016llx Output Prod=%016llx \n",x_op, y_op, z_next);
    return z_next;
}

void gcm_prince_mem_enc_init(const int debug,
                             const unsigned int data_nb_rounds,
                             int conf,
                             const uint64_t in_iv,
                             const uint64_t data_key0, const uint64_t data_key1,
                             const uint64_t in_ad,
                             uint64_t &h_op, uint64_t &ctr0_op,
                             uint64_t &o_auth_tag)
{

    uint64_t half_enc_st, half_dec_st, data_to_ghash;
    const uint64_t ctr0_inp = 0x616c62616c756365;
    PRINT("PRINCE CTR GCM Cmodel - init stage\n");
    h_op = prince_enc_dec_uint64(0, data_key0, data_key1, 0, data_nb_rounds, conf, half_enc_st, half_dec_st); // encrypt 0 to create H
    // o_data = o_data ^ in_data; // in_data must be 0 in this state, I placed the XOR to testability reasons
    PRINT("GCM_H_ENC: h_op =%llx \n", h_op);
    //------------------------
    ctr0_op = prince_round(data_nb_rounds, ctr0_inp, 1, in_iv); // to get the ctr0 it's necessary to XOR back in_data
    ctr0_op = prince_enc_dec_uint64(ctr0_op, data_key0, data_key1, 0, data_nb_rounds, conf, half_enc_st, half_dec_st);
    o_auth_tag = ctr0_op ^ ghash_mul(h_op, in_ad);
    PRINT("GCM_CTR0_ENC: ctr0_op =%llx, o_auth_tag=%llx \n", ctr0_op, o_auth_tag);
}

void gcm_prince_mem_enc_block(const int debug,
                              const unsigned int data_nb_rounds,
                              int conf,
                              int dec,
                              uint64_t in_data,
                              const uint64_t in_iv,
                              uint64_t in_address,
                              const uint64_t data_key0, const uint64_t data_key1,
                              const uint64_t in_ad,
                              uint64_t h_op, uint64_t ctr0_op,
                              uint64_t &o_data, uint64_t &o_auth_tag)
{

    uint64_t half_enc_st, half_dec_st, data_to_ghash, prev_tag;

    PRINT("PRINCE CTR GCM Cmodel - block stage\n");
    ctr_prince_mem_enc(debug, data_nb_rounds, conf, 2, in_data, in_iv, in_address, data_key0, data_key1, o_data);
    prev_tag = o_auth_tag ^ ctr0_op;
    data_to_ghash = (dec == 1) ? in_data : o_data;
    o_auth_tag = ctr0_op ^ ghash_mul(h_op, data_to_ghash ^ prev_tag); // theoretically the ctr0_op should be XORed at the end but hardware wise is constanly xored
    PRINT("GCM_CTRN_ENC : o_data =%llx, o_auth_tag=%llx \n", o_data, o_auth_tag);
}

void gcm_prince_mem_enc_finalize(const int debug,
                                 unsigned int nb_blocks,
                                 uint64_t h_op, uint64_t ctr0_op,
                                 uint64_t prev_tag,
                                 uint64_t &o_auth_tag)
{

    uint64_t data_width = 64; // 64 is because othe data width in Prince
    uint64_t counter = nb_blocks * 64;
    uint64_t len_a_c = (data_width << 33) | counter;
    prev_tag = prev_tag ^ ctr0_op;
    o_auth_tag = ctr0_op ^ ghash_mul(h_op, len_a_c ^ prev_tag);
    PRINT("GCM_TAG_DONE:lenac= %llx ghash_in =%llx, o_auth_tag=%llx \n", len_a_c, len_a_c ^ prev_tag, o_auth_tag);
}
/*  GCM PRINCE FUNCTION   */
void gcm_prince_mem_enc(const int debug,
                        const unsigned int data_nb_rounds,
                        const unsigned int block_num,
                        int conf,
                        int mode,
                        int dec,
                        uint64_t in_data[],
                        const uint64_t in_iv,
                        uint64_t in_address[],
                        const uint64_t data_key0, const uint64_t data_key1,
                        const uint64_t in_ad,
                        uint64_t o_data[], uint64_t &o_auth_tag)
{

    uint64_t prev_tag, h_op, ctr0_op, len_a_c = 0;

    uint64_t half_enc_st, half_dec_st, data_to_ghash;
    const uint64_t ctr0_inp = 0x616c62616c756365;

    PRINT("PRINCE CTR GCM Cmodel \n");
    h_op = prince_enc_dec_uint64(0, data_key0, data_key1, 0, data_nb_rounds, conf, half_enc_st, half_dec_st); // encrypt 0 to create H
                                                                                                              // o_data = o_data ^ in_data; // in_data must be 0 in this state, I placed the XOR to testability reasons
    PRINT("GCM_H_ENC: h_op =%llx \n", h_op);
    //------------------------
    ctr0_op = prince_round(12, ctr0_inp, 1, in_iv); // to get the ctr0 it's necessary to XOR back in_data
    ctr0_op = prince_enc_dec_uint64(ctr0_op, data_key0, data_key1, 0, data_nb_rounds, conf, half_enc_st, half_dec_st);
    o_auth_tag = ctr0_op ^ ghash_mul(h_op, in_ad);
    PRINT("GCM_CTR0_ENC: ctr0_op =%llx, o_auth_tag=%llx \n", ctr0_op, o_auth_tag);

    //------------------------
    PRINT("GCM_CTRN_ENC before: o_data =%llx, o_auth_tag=%llx \n", o_data, o_auth_tag);
    for (int i = 0; i < block_num; i++)
    {
        ctr_prince_mem_enc(debug, data_nb_rounds, conf, mode, in_data[i], in_iv, in_address[i], data_key0, data_key1, o_data[i]);
        // PRINT("GCM_CTRN_ENC Middle \n");
        prev_tag = o_auth_tag ^ ctr0_op;
        data_to_ghash = (dec == 1) ? in_data[i] : o_data[i];
        o_auth_tag = ctr0_op ^ ghash_mul(h_op, data_to_ghash ^ prev_tag); // theoretically the ctr0_op should be XORed at the end but hardware wise is constanly xored
        PRINT("GCM_CTRN_ENC %d : o_data =%llx, o_auth_tag=%llx \n", i, o_data[i], o_auth_tag);
    }
    //------------------------
    //       o_auth_tag = ctr0_op ^ ghash_mul(h_op , prev_data ^ prev_tag ) ;
    //       PRINT("GCM_LAST_DGHASH: ghash_in =%llx, o_auth_tag=%llx \n",prev_data ^ prev_tag,o_auth_tag);
    //------------------------
    uint64_t data_width = 64; // 64 is because othe data width in Prince
    uint64_t counter = block_num * 64;
    len_a_c = (data_width << 33) | counter;
    prev_tag = o_auth_tag ^ ctr0_op;
    o_auth_tag = ctr0_op ^ ghash_mul(h_op, len_a_c ^ prev_tag);
    PRINT("GCM_TAG_DONE:lenac= %llx ghash_in =%llx, o_auth_tag=%llx \n", len_a_c, len_a_c ^ prev_tag, o_auth_tag);
    //------------------------
}

/*  GCM PRINCE FUNCTION  state precise*/
void gcm_prince_mem_enc_steps(const int debug,
                              const unsigned int data_nb_rounds,
                              int conf,
                              int mode,
                              int prince_state,
                              const uint64_t in_data,
                              const uint64_t in_iv,
                              const uint64_t in_address,
                              const uint64_t data_key0, const uint64_t data_key1,
                              const uint64_t in_ad,
                              const uint64_t prev_tag,
                              const uint64_t prev_data,
                              const uint64_t h_op,
                              const uint64_t ctr0_op,
                              const uint64_t len_a_c,
                              uint64_t &o_data, uint64_t &o_auth_tag)
{

    uint64_t half_enc_st, half_dec_st;
    const uint64_t ctr0_inp = 0x616c62616c756365;
    o_data = 0;
    o_auth_tag = 0;
    switch (prince_state)
    {
    case IDLE:
        PRINT("IDLE: Prince is not supposed to do anything, combinatorially speaking it will have some outputs not (deliberately) replicable by the Cmodel \n");

        break;
    case GCM_H_ENC:
        o_data = prince_enc_dec_uint64(0, data_key0, data_key1, 0, data_nb_rounds, conf, half_enc_st, half_dec_st); // encrypt 0 to create H
        o_data = o_data ^ in_data;                                                                                  // in_data must be 0 in this state, I placed the XOR to testability reasons
        PRINT("GCM_H_ENC: o_data =%llx, o_auth_tag=%llx \n", o_data, o_auth_tag);
        break;
    case GCM_CTR0_ENC:
        o_data = prince_round(data_nb_rounds, ctr0_inp, 1, in_iv); // to get the ctr0 it's necessary to XOR back in_data
        o_data = prince_enc_dec_uint64(o_data, data_key0, data_key1, 0, data_nb_rounds, conf, half_enc_st, half_dec_st);
        o_auth_tag = ghash_mul(h_op, in_ad);
        PRINT("GCM_CTR0_ENC: h_op:%llx, in_ad:%llx, o_data =%llx, o_auth_tag=%llx, o_auth_tag^ctr0_op:%llx \n", h_op, in_ad, o_data, o_auth_tag, o_auth_tag ^ o_data);
        break;
    case GCM_CTRN_ENC:
        // PRINT("GCM_CTRN_ENC before: o_data =%llx, o_auth_tag=%llx \n",o_data,o_auth_tag);
        ctr_prince_mem_enc(debug, data_nb_rounds, conf, mode, in_data, in_iv, in_address, data_key0, data_key1, o_data);
        PRINT("GCM_CTRN_ENC Middle: prev_data =%llx, o_auth_tag=%llx, prev_tag^ctr0_op \n", prev_data, prev_tag, prev_tag ^ ctr0_op);
        o_auth_tag = ctr0_op ^ ghash_mul(h_op, prev_data ^ prev_tag); // theoretically the ctr0_op should be XORed at the end but hardware wise is constanly xored
        PRINT("GCM_CTRN_ENC : o_data =%llx, o_auth_tag=%llx, o_auth_tag^ctr0_op=%llx \n", o_data, o_auth_tag, o_auth_tag ^ ctr0_op);
        break;
    case GCM_LAST_DGHASH:
        o_auth_tag = ctr0_op ^ ghash_mul(h_op, prev_data ^ prev_tag);
        PRINT("GCM_LAST_DGHASH: ghash_in =%llx, o_auth_tag=%llx \n", prev_data ^ prev_tag, o_auth_tag);
        break;
    case GCM_TAG_DONE:
        o_auth_tag = ctr0_op ^ ghash_mul(h_op, len_a_c ^ prev_tag);
        PRINT("GCM_TAG_DONE: ghash_in =%llx, o_auth_tag=%llx \n", len_a_c ^ prev_tag, o_auth_tag);
        break;
    case CTR_ENC_MODE:
        ctr_prince_mem_enc(debug, data_nb_rounds, conf, mode, in_data, in_iv, in_address, data_key0, data_key1, o_data);
        PRINT("CTR_ENC_MODE: o_data =%llx, o_auth_tag=%llx \n", o_data, o_auth_tag);
        break;
    default:
        PRINT("STATE NOT SUPPORTED \n");
    }
}
#endif //__EOS_REF_H__
