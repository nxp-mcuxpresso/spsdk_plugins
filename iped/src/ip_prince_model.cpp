/*
 * Copyright 2024 NXP
 * All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef __EOS_REF_H__
#define __EOS_REF_H__

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <time.h>

// #define JWF_DEBUG
#define LIB

#ifdef JWF_DEBUG
#define DEBUG(...) printf(__VA_ARGS__)
#else
#define DEBUG(...)
#endif

#define PRINT(...) printf(__VA_ARGS__)

// #include "ip_prince_model.h"
#include "iped_model_c.h"
#include "ip_prince_ctr.h"

FILE *in_fptr;
FILE *out_raw_fptr;
FILE *out_desc_fptr;
char line[1024];
char in_file[128];

// Main wrapper function
PRINCE_EXPORT_API int prince_mem_enc(int nb_blocks, struct test_vec *transaction)
{
    // int prince_mem_enc(uint32_t data_nb_rounds, int transaction->conf, int gcm_en, int nb_blocks, struct test_vec *transaction)   {

    uint32_t data_nb_rounds = 12; // number of rounds
    uint32_t gcm_en = 1;          // GCM hardware enabled
    DEBUG("\nprince_mem_enc - data_nb_rounds:%d, transaction->run_dbl_enc:%d, gcm_en:%d, nb_blocks:%d\n", data_nb_rounds, transaction->run_dbl_enc, gcm_en, nb_blocks);
    int mode_in;

    // Select true mode based on whether GCM hardware is enabled
    if (transaction->mode == 0 && gcm_en == 0)
    {
        mode_in = 0;
    }
    else if (transaction->mode == 0 && gcm_en == 1)
    {
        mode_in = 5;
    }
    else if (transaction->mode == 1 && gcm_en == 1)
    {
        mode_in = 2;
    }
    else if (transaction->mode == 1 && gcm_en == 0)
    {
        PRINT("[ERROR]: Cannot run GCM vectors while gcm mode is not enabled. Exiting.\n");
        return -1;
    }

    if (gcm_en > 1)
    {
        PRINT("[ERROR]: gcm_en must be 0 or 1. Exiting.\n");
        return -1;
    }
    if (transaction->run_dbl_enc > 1)
    {
        PRINT("[ERROR]: transaction->run_dbl_encig  must be either 1 (double encryption) or 0 (single encryption). Exiting.\n");
        return -1;
    }
    if (data_nb_rounds > 12 || data_nb_rounds < 4)
    {
        PRINT("[ERROR]: Number of rounds must be in range 4-12. Exiting.\n");
        return -1;
    }

    if (mode_in == 2)
    { // Call ip_prince_ctr GCM function
        gcm_prince_mem_enc(0, data_nb_rounds, nb_blocks, transaction->run_dbl_enc, mode_in, transaction->dec, transaction->i_data, transaction->iv, transaction->address, transaction->data_key0, transaction->data_key1, transaction->in_ad, transaction->o_data, transaction->o_auth_tag);
    }
    else if (mode_in == 0 || mode_in == 5)
    { // Call ip_prince_ctr CTR function
        ctr_prince_mem_enc(0, data_nb_rounds, transaction->run_dbl_enc, mode_in, *transaction->i_data, transaction->iv, *transaction->address, transaction->data_key0, transaction->data_key1, *transaction->o_data);
    }
    DEBUG("prince_mem_enc - Transaction\nmode:%llx\ndec:%llx\nnb_blocks:%llx\n\n", transaction->mode, transaction->dec, nb_blocks);
    DEBUG("\ni_data:%llx", *transaction->i_data);
    if (mode_in == 2)
    {
        for (int i = 1; i < nb_blocks; i++)
        {
            DEBUG("\ni_data %d:%llx", i, *(transaction->i_data + i));
        }
    }
    DEBUG("\naddress:%llx", *transaction->address);
    if (mode_in == 2)
    {
        for (int i = 1; i < nb_blocks; i++)
        {
            DEBUG("\naddress %d:%llx", i, *(transaction->address + i));
        }
    }
    DEBUG("\niv:%llx\nin_ad:%llx\ndata_key0:%llx\ndata_key1:%llx", transaction->iv, transaction->in_ad, transaction->data_key0, transaction->data_key1);
    DEBUG("\no_data:%llx", *transaction->o_data);
    if (mode_in == 2)
    {
        for (int i = 1; i < nb_blocks; i++)
        {
            DEBUG("\no_data %d:%llx", i, *(transaction->o_data + i));
        }
    }
    DEBUG("\no_auth_tag:%llx", transaction->o_auth_tag);
    return 1;
}

// Generate one vector randomly
int gen_rand_vec(struct test_vec *rand_vec, uint32_t nb_blocks, uint32_t random_mode, uint32_t random_decrypt, uint32_t incr_addr, uint32_t incr_num, uint32_t const_key, uint32_t const_iv, uint32_t first_run, int prev_mode)
{

    DEBUG("\ngen_rand_vec - nb_blocks = %d, random_mode = %d, random_decrypt = %d, incr_addr = %d, incr_num = %d, const_key = %d, const_iv = %d, first_run = %d\n", nb_blocks, random_mode, random_decrypt, incr_addr, incr_num, const_key, const_iv, first_run);

    if (random_mode == 0)
    { // ctr mode is selected for whole test
        rand_vec->mode = 0;
    }
    else if (random_mode == 1)
    { // gcm mode is selected for whole test
        rand_vec->mode = 1;
    }
    else if (random_mode == 2)
    { // select mode randomly on each iteration
        rand_vec->mode = rand() % 2;
    }
    if (random_decrypt == 0)
    { // encryption is selected for whole test
        rand_vec->dec = 0;
    }
    else if (random_decrypt == 1)
    { // decryption mode is selected for whole test
        rand_vec->dec = 1;
    }
    else if (random_decrypt == 2)
    { // select randomly on each iteration
        rand_vec->dec = rand() % 2;
    }

    if (rand_vec->mode == 0)
    { // Generate one CTR vector

        *rand_vec->i_data = ((uint64_t)rand() << 32) | (uint64_t)rand();
        if (first_run || !const_iv)
        {
            rand_vec->iv = ((uint64_t)rand() << 32) | (uint64_t)rand();
        }
        if (first_run || !incr_addr)
        {
            *rand_vec->address = (uint64_t)rand();
        }
        else
        {
            if (prev_mode == 1)
            {
                *(rand_vec->address) = (*(rand_vec->address)) + incr_num * nb_blocks;
            }
            else
            {
                *rand_vec->address = *rand_vec->address + incr_num;
            }
        }
        if (first_run || !const_key)
        {
            rand_vec->data_key0 = ((uint64_t)rand() << 32) | (uint64_t)rand();
            rand_vec->data_key1 = ((uint64_t)rand() << 32) | (uint64_t)rand();
        }
        rand_vec->in_ad = 0;
        rand_vec->o_auth_tag = 0;
        DEBUG("gen_rand_vec - rand_vec->data:%llx\nrand_vec->iv:%llx\nrand_vec->addresa:%llx\nrand_vec->data_key0:%llx\nrand_vec->data_key1:%llx\nrand_vec->o_data:%d\n\n", rand_vec->i_data, rand_vec->iv, rand_vec->address, rand_vec->data_key0, rand_vec->data_key1, rand_vec->o_data);
    }
    else if (rand_vec->mode == 1)
    { // Generate one GCM vector

        if (first_run || !const_iv)
        {
            rand_vec->iv = ((uint64_t)rand() << 32) | (uint64_t)rand();
        }
        rand_vec->in_ad = ((uint64_t)rand() << 32) | (uint64_t)rand();
        if (first_run || !const_key)
        {
            rand_vec->data_key0 = ((uint64_t)rand() << 32) | (uint64_t)rand();
            rand_vec->data_key1 = ((uint64_t)rand() << 32) | (uint64_t)rand();
        }
        rand_vec->o_auth_tag = 0;
        if (!incr_addr)
        {
            for (int i = 0; i < nb_blocks; i++)
            {
                *(rand_vec->address + i) = (uint64_t)rand();
            }
        }
        else if (first_run)
        {
            *(rand_vec->address) = (uint64_t)rand();
            for (int i = 1; i < nb_blocks; i++)
            {
                *(rand_vec->address + i) = *(rand_vec->address + i - 1) + incr_num;
            }
        }
        else
        {
            if (prev_mode == 1)
            {
                *(rand_vec->address) = (*(rand_vec->address)) + incr_num * nb_blocks;
            }
            else
            {
                *rand_vec->address = *rand_vec->address + incr_num;
            }
            for (int i = 1; i < nb_blocks; i++)
            {
                *(rand_vec->address + i) = *(rand_vec->address + i - 1) + incr_num;
            }
        }
        for (int i = 0; i < nb_blocks; i++)
        {
            *(rand_vec->i_data + i) = ((uint64_t)rand() << 32) | (uint64_t)rand();
        }
        DEBUG("gen_rand_vec - rand_vec->mode:%llx\nrand_vec->dec:%llx\nrand_vec->iv:%llx\nrand_vec->in_ad:%llx\nrand_vec->data_key0:%llx\nrand_vec->data_key1:%llx\n\n", rand_vec->mode, rand_vec->dec, rand_vec->iv, rand_vec->in_ad, rand_vec->data_key0, rand_vec->data_key1);
    }
    else
    { // Exit with ERROR if neither CTR or GCM mode specified
        PRINT("[ERROR]: Mode must be either 0 (CTR) or 1 (GCM). Exiting.\n");
        return -1;
    }
    return 1;
}

// Read one vector from file
int read_vec_from_file(struct test_vec *input_vec, uint32_t nb_blocks)
{
    int commai = 0; // number of commas
    int offset;
    char *line_char = line;
    int mode, dec; // TODO remove

    uint64_t iv, data_key0, data_key1, address, i_data, auth_tag; // TODO remove
    if (fgets(line_char, 1024, in_fptr))
    { // get one line from in_fptr
        // Count commas
        for (int i = 0; line[i] != '\n'; i++)
        {
            if (line[i] == ',')
            {
                commai++;
            }
        }

        mode = atoi(line); // Read mode
        DEBUG("\nread_vec_from_file - mode:%d\n", mode);

        // Exit with error if number of vectors (commas) is incorrect
        if ((mode == 0 && commai < 6) || (mode == 1 && commai < 6 + nb_blocks))
        {
            PRINT("[ERROR]: Incorrect vector format. Exiting.\n");
            return -1;
        }

        if (mode == 0)
        { // Read one ctr vector
            sscanf(line_char, "%x,%x,%llx,%llx,%llx,%llx,%llx", &mode, &dec, &iv, &data_key0, &data_key1, &address, &i_data);
            input_vec->mode = mode;
            input_vec->dec = dec;
            *input_vec->i_data = i_data;
            input_vec->iv = iv;
            *input_vec->address = address;
            input_vec->data_key0 = data_key0;
            input_vec->data_key1 = data_key1;
            input_vec->in_ad = 0;
            input_vec->o_auth_tag = 0;
            DEBUG("read_vec_from_file - input_vec->mode:%llx\ninput_vec->dec:%llx\ninput_vec->i_data:%llx\ninput_vec->iv:%llx\ninput_vec->address:%llx\ninput_vec->data_key0:%llx\ninput_vec->data_key1:%llx\n\n", input_vec->mode, input_vec->dec, input_vec->i_data[0], input_vec->iv, input_vec->address, input_vec->data_key0, input_vec->data_key1);
        }
        else if (mode == 1)
        { // Read one gcm vector
            sscanf(line_char, "%x,%x,%llx,%llx,%llx,%llx%n", &(input_vec->mode), &(input_vec->dec), &(input_vec->iv), &(input_vec->in_ad), &(input_vec->data_key0), &(input_vec->data_key1), &offset);
            line_char += offset;
            for (int i = 0; i < nb_blocks; i++)
            {
                sscanf(line_char, ",%llx%n", &address, &offset);
                line_char += offset;
                DEBUG("address_temp%d:%llx\n", i, address);
                *((input_vec->address) + i) = address;
            }
            for (int i = 0; i < nb_blocks; i++)
            {
                sscanf(line_char, ",%llx%n", &i_data, &offset);
                line_char += offset;
                DEBUG("i_data_temp%d:%llx\n", i, i_data);
                *((input_vec->i_data) + i) = i_data;
            }
            sscanf(line_char, ",%llx%n", &auth_tag, &offset);
            line_char += offset;
            DEBUG("auth_tag_temp:%llx\n", auth_tag);
            input_vec->in_auth_tag = auth_tag;
            input_vec->o_auth_tag = 0;
            DEBUG("read_vec_from_file - input_vec->mode:%llx\ninput_vec->dec:%llx\ninput_vec->iv:%llx\ninput_vec->in_ad:%llx\ninput_vec->data_key0:%llx\ninput_vec->data_key1:%llx\n,input_vec->in_auth_tag:%llx\n", input_vec->mode, input_vec->dec, input_vec->iv, input_vec->in_ad, input_vec->data_key0, input_vec->data_key1, input_vec->in_auth_tag);
            for (int i = 0; i < nb_blocks; i++)
            {
                DEBUG("input_vec->address%d:%llx\n", i, *((input_vec->address) + i));
            }
            for (int i = 0; i < nb_blocks; i++)
            {
                DEBUG("input_vec->i_data%d:%llx\n", i, *((input_vec->i_data) + i));
            }
            DEBUG("\n");
        }
        else
        { // Exit with ERROR if neither CTR or GCM mode specified
            PRINT("[ERROR]: Mode must be either 0 (CTR) or 1 (GCM). Exiting.\n");
            return -1;
        }
        return 1;
    }
    else
    { // Exit if no further line to read
        PRINT("Reached end of file. Exiting\n");
        return 0;
    }
}

#ifndef LIB
int main(int argc, char *argv[])
{
    struct test_vec transaction;

    uint32_t data_nb_rounds;                                                            // number of rounds
    uint32_t config;                                                                    // 0 = single encryption, 1 = double encryption
    uint32_t nb_vectors;                                                                // number of test vectors to read in or generate
    uint32_t gcm_en;                                                                    // GCM hardware enabled
    uint32_t nb_blocks;                                                                 // number of GCM blocks
    uint32_t rand;                                                                      // use random test vectors if 1, vectors from file if 0
    uint32_t random_mode, random_decrypt, const_key, const_iv, incr_addr, incr_num = 0; // random generation parameters
    char input_char;                                                                    // temporary input character

    //  Read configuration from standard input
    PRINT("PRINCE CMODEL\n");
    PRINT("Number of rounds:\n");
    scanf("%d", &data_nb_rounds);
    PRINT("Config (0 or 1):\n");
    scanf("%d", &config);
    PRINT("Number of vectors:\n");
    scanf("%d", &nb_vectors);
    PRINT("Enable GCM hardware support (y/n):\n");
    scanf(" %c", &input_char);
    if (input_char == 'y')
    {
        gcm_en = 1;
    }
    else if (input_char == 'n')
    {
        gcm_en = 0;
    }
    else
    {
        PRINT("[ERROR] Neither y or n provided. Exiting\n");
        return -1;
    }
    PRINT("Number of blocks in GCM mode:\n");
    scanf("%d", &nb_blocks);
    if (nb_blocks == 0)
    {
        nb_blocks == 1;
    }
    PRINT("Enable random vector generation (y/n):\n");
    scanf(" %c", &input_char);
    if (input_char == 'y')
    {
        rand = 1;
    }
    else if (input_char == 'n')
    {
        rand = 0;
    }
    else
    {
        PRINT("[ERROR] Neither y or n provided. Exiting\n");
        return -1;
    }
    if (rand == 1)
    {
        PRINT("Generate CTR only (c), GCM only (g) or mixed vectors (m):\n");
        scanf(" %c", &input_char);
        if (input_char == 'c')
        {
            random_mode = 0;
        }
        else if (input_char == 'g')
        {
            random_mode = 1;
        }
        else if (input_char == 'm')
        {
            random_mode = 2;
        }
        else
        {
            PRINT("[ERROR] Neither c, g or m provided. Exiting\n");
            return -1;
        }
        PRINT("Generate decryption only (d), encryption only (e) or mixed vectors (m):\n");
        scanf(" %c", &input_char);
        if (input_char == 'e')
        {
            random_decrypt = 0;
        }
        else if (input_char == 'd')
        {
            random_decrypt = 1;
        }
        else if (input_char == 'm')
        {
            random_decrypt = 2;
        }
        else
        {
            PRINT("[ERROR] Neither c, g or m provided. Exiting\n");
            return -1;
        }
        PRINT("Maintain a constant key (y/n):\n");
        scanf(" %c", &input_char);
        if (input_char == 'y')
        {
            const_key = 1;
        }
        else if (input_char == 'n')
        {
            const_key = 0;
        }
        else
        {
            PRINT("[ERROR] Neither y or n provided. Exiting\n");
            return -1;
        }
        PRINT("Maintain a constant iv (y/n):\n");
        scanf(" %c", &input_char);
        if (input_char == 'y')
        {
            const_iv = 1;
        }
        else if (input_char == 'n')
        {
            const_iv = 0;
        }
        else
        {
            PRINT("[ERROR] Neither y or n provided. Exiting\n");
            return -1;
        }
        PRINT("Increment address (y/n):\n");
        scanf(" %c", &input_char);
        if (input_char == 'y')
        {
            incr_addr = 1;
            PRINT("Number to increment address by in hex:\n");
            scanf("%x", &incr_num);
        }
        else if (input_char == 'n')
        {
            incr_addr = 0;
            incr_num = 0;
        }
        else
        {
            PRINT("[ERROR] Neither y or n provided. Exiting\n");
            return -1;
        }
    }
    else
    {
        PRINT("Input vector file:\n");
        scanf("%s", in_file);
    }

    // Write status message back to standard output
    PRINT("Running %d", nb_vectors);
    if (rand == 1)
    {
        PRINT(" random test vectors.\n");
    }
    if (rand == 0)
    {
        PRINT(" test vectors from file.\n");
    }
    PRINT("Prince configuration - number of rounds:%d, config:%d, gcm hardware enabled:%d, number of gcm blocks:%d\n", data_nb_rounds, config, gcm_en, nb_blocks);

    if (rand == 1)
    { // Initialize RNG
        time_t t;
        srand((unsigned)time(&t));
    }
    else
    { // Open input vector file
        in_fptr = fopen(in_file, "r");
        if (in_fptr == NULL)
        {
            PRINT("[ERROR] Failed to open input file. Exiting.\n");
            return -1;
        }
    }

    // Open output vector file
    out_desc_fptr = fopen("prince_model_vectors", "w");
    out_raw_fptr = fopen("prince_model_vectors_raw", "w");
    if (out_desc_fptr == NULL || out_raw_fptr == NULL)
    {
        PRINT("[ERROR] Failed to open output files for writing. Exiting\n");
        return -1;
    }

    int first_run = 1; // Variable to intialize key, iv and address to random value only once
    int prev_mode = 0; // Variable to keep track of mode of previous vector for random generation

    // Allocate memory to transaction pointers. nb_blocks set to min 1 if ctr vectors only
    transaction.i_data = (uint64_t *)calloc(nb_blocks, sizeof(uint64_t));
    transaction.address = (uint64_t *)calloc(nb_blocks, sizeof(uint64_t));
    transaction.o_data = (uint64_t *)calloc(nb_blocks, sizeof(uint64_t));

    // Iterate over all vectors
    for (int i = 0; i < nb_vectors; i++)
    {
        DEBUG("\n\nVector: %d\n", i);
        if (rand == 1)
        { // Generate one vector randomly
            if (gen_rand_vec(&transaction, nb_blocks, random_mode, random_decrypt, incr_addr, incr_num, const_key, const_iv, first_run, prev_mode) != 1)
            {
                return -1; // Exit with error if gen_rand_vec does not return 1
            }
            first_run = 0; // Set to 0 after first iteration. Prevents rerandomizing key, iv and address.
        }
        else
        { // Read one vector from file
            if (read_vec_from_file(&transaction, nb_blocks) != 1)
            {
                PRINT("Vectors written to prince_model_vectors and prince_model_vectors_raw. Exiting.\n");
                return 0; // Exit if read_vec_from_file does not return 1
            }
        }

        if (prince_mem_enc(data_nb_rounds, config, gcm_en, nb_blocks, &transaction) != 1)
        {              // Run one transaction
            return -1; // Exit with error if prince_mem_enc does not return 1
        }

        // Write result to file
        if (transaction.mode == 0)
        { // CTR vector
            fprintf(out_raw_fptr, "%llx,%llx,%016llx,%016llx,%016llx,%08llx,%016llx,%016llx\n", transaction.mode, transaction.dec, transaction.iv, transaction.data_key0, transaction.data_key1, *transaction.address, *transaction.i_data, *transaction.o_data);
            fprintf(out_desc_fptr, "Mode:%llx, Dec:%llx, IV:%16llx, Key 0:%16llx, Key 1:%16llx, Address:%8llx, Input data:%16llx, Output Data:%16llx\n", transaction.mode, transaction.dec, transaction.iv, transaction.data_key0, transaction.data_key1, *transaction.address, *transaction.i_data, *transaction.o_data);
            prev_mode = 0;
        }
        else if (transaction.mode == 1)
        { // GCM vector
            fprintf(out_raw_fptr, "%llx,%llx,%016llx,%016llx,%016llx,%016llx,", transaction.mode, transaction.dec, transaction.iv, transaction.in_ad, transaction.data_key0, transaction.data_key1);
            for (int i = 0; i < nb_blocks; i++)
            {
                fprintf(out_raw_fptr, "%08llx,", *(transaction.address + i));
            }
            for (int i = 0; i < nb_blocks; i++)
            {
                fprintf(out_raw_fptr, "%016llx,", *(transaction.i_data + i));
            }
            if (rand == 1)
            { // If vectors are randomly generated set input auth_tag to output auth tag if decrypting and to 0 if encrypting
                if (transaction.dec == 1)
                {
                    fprintf(out_raw_fptr, "%016llx,", transaction.o_auth_tag);
                }
                else if (transaction.dec == 0)
                {
                    fprintf(out_raw_fptr, "%016llx,", 0);
                }
            }
            else if (rand == 0)
            { // If vectors are read from file use same auth_tag as in input vectors
                fprintf(out_raw_fptr, "%016llx,", transaction.in_auth_tag);
            }
            for (int i = 0; i < nb_blocks; i++)
            {
                fprintf(out_raw_fptr, "%016llx,", *(transaction.o_data + i));
            }
            fprintf(out_raw_fptr, "%016llx\n", transaction.o_auth_tag);

            fprintf(out_desc_fptr, "Mode:%llx, Dec:%llx, IV:%16llx, AD:%16llx, Key 0:%16llx, Key 1:%16llx,", transaction.mode, transaction.dec, transaction.iv, transaction.in_ad, transaction.data_key0, transaction.data_key1);
            for (int i = 0; i < nb_blocks; i++)
            {
                fprintf(out_desc_fptr, " Address %d:%8llx,", i, *(transaction.address + i));
            }
            for (int i = 0; i < nb_blocks; i++)
            {
                fprintf(out_desc_fptr, " Input Data %d:%16llx,", i, *(transaction.i_data + i));
            }
            if (rand == 1)
            {
                if (transaction.dec == 1)
                {
                    fprintf(out_desc_fptr, "In Auth Tag:%16llx,", transaction.o_auth_tag);
                }
                else if (transaction.dec == 0)
                {
                    fprintf(out_desc_fptr, "In Auth Tag:%16llx,", 0);
                }
            }
            else if (rand == 0)
            {
                fprintf(out_desc_fptr, "In Auth Tag:%16llx,", transaction.in_auth_tag);
            }
            for (int i = 0; i < nb_blocks; i++)
            {
                fprintf(out_desc_fptr, " Output Data %d:%16llx,", i, *(transaction.o_data + i));
            }
            fprintf(out_desc_fptr, "Out Auth Tag:%16llx\n", transaction.o_auth_tag);
            prev_mode = 1;
        }
    }

    free(transaction.i_data);
    free(transaction.address);
    free(transaction.o_data);
    PRINT("Vectors written to prince_model_vectors and prince_model_vectors_raw. Exiting.\n");
    return 1;
}
#endif // LIB

#endif //__EOS_REF_H__
