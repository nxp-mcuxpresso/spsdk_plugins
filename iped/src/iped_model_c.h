/*
 * Copyright 2024 NXP
 * All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef IP_PRINCE_MODEL
#define IP_PRINCE_MODEL

#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#if defined(_WIN32)
#define PRINCE_EXPORT_API __declspec(dllexport)
#else
#define PRINCE_EXPORT_API
#endif

typedef struct test_vec
{
    uint32_t mode;
    uint32_t dec;
    uint32_t run_dbl_enc;
    uint64_t *i_data;
    uint64_t iv;
    uint64_t *address;
    uint64_t data_key0;
    uint64_t data_key1;
    uint64_t *o_data;
    uint64_t in_ad;
    uint64_t in_auth_tag;
    uint64_t o_auth_tag;
} test_vec;

#pragma once
#ifdef __cplusplus
extern "C"
{
#endif

    PRINCE_EXPORT_API int prince_mem_enc(int n_blocks, test_vec *iped_vector);

#ifdef __cplusplus
}
#endif

#endif
