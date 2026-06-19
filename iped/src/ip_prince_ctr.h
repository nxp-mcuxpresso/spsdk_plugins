/*
 * Copyright 2024 NXP
 * All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef IP_PRINCE_CTR
#define IP_PRINCE_CTR

#include <stdint.h>
#include <string.h>
#include <cstdio>

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

void ctr_prince_mem_enc(const int debug,
                        const unsigned int data_nb_rounds,
                        int conf,
                        int mode,
                        const uint64_t in_data,
                        const uint64_t in_iv,
                        const uint64_t in_address,
                        const uint64_t data_key0, const uint64_t data_key1,
                        uint64_t &o_data);

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
                        uint64_t o_data[], uint64_t &o_auth_tag);

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
                              uint64_t &o_data, uint64_t &o_auth_tag);
void gcm_prince_mem_enc_init(const int debug,
                             const unsigned int data_nb_rounds,
                             int conf,
                             const uint64_t in_iv,
                             const uint64_t data_key0, const uint64_t data_key1,
                             const uint64_t in_ad,
                             uint64_t &h_op, uint64_t &ctr0_op,
                             uint64_t &o_auth_tag);

void gcm_prince_mem_enc_finalize(const int debug,
                                 unsigned int nb_blocks,
                                 uint64_t h_op, uint64_t ctr0_op,
                                 uint64_t prev_tag,
                                 uint64_t &o_auth_tag);

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
                              uint64_t &o_data, uint64_t &o_auth_tag);
#endif
