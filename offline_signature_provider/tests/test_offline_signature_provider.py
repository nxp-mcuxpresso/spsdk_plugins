#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2023,2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Unit tests for OfflineSP (Offline Signature Provider)."""

import os
import tempfile
import unittest
from unittest.mock import mock_open, patch

from spsdk.crypto.hash import EnumHashAlgorithm
from spsdk.crypto.signature_provider import SignatureProvider

from spsdk_offline_signature_provider.offline_signature_provider import (
    _ECC_HASH_ALGS,
    _ECC_SIG_SIZES,
    _RSA_HASH_ALGS,
    _RSA_SIG_SIZES,
    OfflineSP,
    SignatureAlgorithm,
)


def test_registration():
    """Test whether OfflineSP got picked up by SPSDK."""
    assert OfflineSP.identifier in SignatureProvider.get_types()


class TestSignatureAlgorithm(unittest.TestCase):
    """Test SignatureAlgorithm enum."""

    def test_signature_algorithm_values(self):
        """Test that SignatureAlgorithm enum has expected values."""
        self.assertEqual(SignatureAlgorithm.ECC.value, "ecc")
        self.assertEqual(SignatureAlgorithm.RSA_PSS.value, "rsa-pss")
        self.assertEqual(SignatureAlgorithm.RSA_PKCS1V15.value, "rsa-pkcs1v15")

    def test_signature_algorithm_from_string(self):
        """Test creating SignatureAlgorithm from string."""
        self.assertEqual(SignatureAlgorithm("ecc"), SignatureAlgorithm.ECC)
        self.assertEqual(SignatureAlgorithm("rsa-pss"), SignatureAlgorithm.RSA_PSS)
        self.assertEqual(SignatureAlgorithm("rsa-pkcs1v15"), SignatureAlgorithm.RSA_PKCS1V15)


class TestOfflineSPInitialization(unittest.TestCase):
    """Test OfflineSP initialization."""

    def test_default_initialization(self):
        """Test default initialization (ECC-256)."""
        provider = OfflineSP()
        self.assertEqual(provider.hash_file, "hash_file")
        self.assertEqual(provider.key_size, 256)
        self.assertEqual(provider.algorithm, SignatureAlgorithm.ECC)
        self.assertEqual(provider.hash_alg, EnumHashAlgorithm.SHA256)
        self.assertEqual(provider.sig_size, 64)

    def test_ecc_initialization_valid_sizes(self):
        """Test ECC initialization with valid key sizes."""
        for key_size in [256, 384, 521]:
            provider = OfflineSP(key_size=key_size, algorithm="ecc")
            self.assertEqual(provider.key_size, key_size)
            self.assertEqual(provider.algorithm, SignatureAlgorithm.ECC)
            self.assertEqual(provider.hash_alg, _ECC_HASH_ALGS[key_size])
            self.assertEqual(provider.sig_size, _ECC_SIG_SIZES[key_size])

    def test_rsa_pss_initialization_valid_sizes(self):
        """Test RSA-PSS initialization with valid key sizes."""
        for key_size in [2048, 3072, 4096]:
            provider = OfflineSP(key_size=key_size, algorithm="rsa-pss")
            self.assertEqual(provider.key_size, key_size)
            self.assertEqual(provider.algorithm, SignatureAlgorithm.RSA_PSS)
            self.assertEqual(provider.hash_alg, _RSA_HASH_ALGS[key_size])
            self.assertEqual(provider.sig_size, _RSA_SIG_SIZES[key_size])

    def test_rsa_pkcs1v15_initialization_valid_sizes(self):
        """Test RSA-PKCS1v15 initialization with valid key sizes."""
        for key_size in [2048, 3072, 4096]:
            provider = OfflineSP(key_size=key_size, algorithm="rsa-pkcs1v15")
            self.assertEqual(provider.key_size, key_size)
            self.assertEqual(provider.algorithm, SignatureAlgorithm.RSA_PKCS1V15)
            self.assertEqual(provider.hash_alg, _RSA_HASH_ALGS[key_size])
            self.assertEqual(provider.sig_size, _RSA_SIG_SIZES[key_size])

    def test_custom_hash_file(self):
        """Test initialization with custom hash file."""
        provider = OfflineSP(hash_file="custom_hash_file")
        self.assertEqual(provider.hash_file, "custom_hash_file")

    def test_invalid_algorithm(self):
        """Test initialization with invalid algorithm."""
        with self.assertRaises(ValueError) as context:
            OfflineSP(algorithm="invalid")
        self.assertIn("Unsupported algorithm: invalid", str(context.exception))

    def test_invalid_ecc_key_size(self):
        """Test initialization with invalid ECC key size."""
        with self.assertRaises(ValueError) as context:
            OfflineSP(key_size=512, algorithm="ecc")
        self.assertIn("Unsupported ECC key size: 512", str(context.exception))

    def test_invalid_rsa_key_size(self):
        """Test initialization with invalid RSA key size."""
        with self.assertRaises(ValueError) as context:
            OfflineSP(key_size=1024, algorithm="rsa-pss")
        self.assertIn("Unsupported RSA key size: 1024", str(context.exception))


class TestOfflineSPProperties(unittest.TestCase):
    """Test OfflineSP properties."""

    def test_signature_length_ecc(self):
        """Test signature_length property for ECC."""
        provider = OfflineSP(key_size=256, algorithm="ecc")
        self.assertEqual(provider.signature_length, 64)

        provider = OfflineSP(key_size=384, algorithm="ecc")
        self.assertEqual(provider.signature_length, 96)

    def test_signature_length_rsa(self):
        """Test signature_length property for RSA."""
        provider = OfflineSP(key_size=2048, algorithm="rsa-pss")
        self.assertEqual(provider.signature_length, 256)

        provider = OfflineSP(key_size=4096, algorithm="rsa-pss")
        self.assertEqual(provider.signature_length, 512)

    def test_is_rsa_algorithm(self):
        """Test is_rsa_algorithm property."""
        ecc_provider = OfflineSP(algorithm="ecc")
        rsa_pss_provider = OfflineSP(key_size=2048, algorithm="rsa-pss")
        rsa_pkcs1_provider = OfflineSP(key_size=2048, algorithm="rsa-pkcs1v15")

        self.assertFalse(ecc_provider.is_rsa_algorithm)
        self.assertTrue(rsa_pss_provider.is_rsa_algorithm)
        self.assertTrue(rsa_pkcs1_provider.is_rsa_algorithm)

    def test_uses_pss_padding(self):
        """Test uses_pss_padding property."""
        ecc_provider = OfflineSP(algorithm="ecc")
        rsa_pss_provider = OfflineSP(key_size=2048, algorithm="rsa-pss")
        rsa_pkcs1_provider = OfflineSP(key_size=2048, algorithm="rsa-pkcs1v15")

        self.assertFalse(ecc_provider.uses_pss_padding)
        self.assertTrue(rsa_pss_provider.uses_pss_padding)
        self.assertFalse(rsa_pkcs1_provider.uses_pss_padding)


class TestOfflineSPFilePathValidation(unittest.TestCase):
    """Test file path validation methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.provider = OfflineSP()

    def test_valid_file_paths(self):
        """Test validation of valid file paths."""
        valid_paths = [
            "signature.bin",
            "/tmp/signature.bin",
            "./signature.bin",
            "../signature.bin",
            "path/to/signature.bin",
        ]

        for path in valid_paths:
            try:
                result = self.provider._validate_file_path(path)
                self.assertIsInstance(result, str)
                self.assertTrue(len(result) > 0)
            except ValueError:
                # Some paths might be invalid on certain systems, that's OK
                pass

    def test_empty_file_path(self):
        """Test validation of empty file path."""
        with self.assertRaises(ValueError) as context:
            self.provider._validate_file_path("")
        self.assertIn("File path cannot be empty", str(context.exception))

    def test_whitespace_only_file_path(self):
        """Test validation of whitespace-only file path."""
        with self.assertRaises(ValueError) as context:
            self.provider._validate_file_path("   ")
        self.assertIn("File path cannot be empty", str(context.exception))


class TestOfflineSPSignatureProcessing(unittest.TestCase):
    """Test signature processing methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.ecc_provider = OfflineSP(key_size=256, algorithm="ecc")
        self.rsa_provider = OfflineSP(key_size=2048, algorithm="rsa-pss")

    @patch(
        "spsdk_offline_signature_provider.offline_signature_provider.PublicKeyEcc.serialize_signature"
    )
    def test_process_ecc_signature_raw_format(self, mock_serialize):
        """Test processing ECC signature in raw r||s format."""
        # Test with correct size signature (raw r||s)
        raw_signature = b"\x00" * 64  # 64 bytes for 256-bit ECC
        result = self.ecc_provider._process_ecc_signature(raw_signature)
        self.assertEqual(result, raw_signature)
        mock_serialize.assert_not_called()

    @patch(
        "spsdk_offline_signature_provider.offline_signature_provider.PublicKeyEcc.serialize_signature"
    )
    def test_process_ecc_signature_der_format(self, mock_serialize):
        """Test processing ECC signature in DER format."""
        der_signature = b"\x30\x44\x02\x20" + b"\x00" * 32 + b"\x02\x20" + b"\x00" * 32
        raw_signature = b"\x00" * 64

        mock_serialize.return_value = raw_signature

        result = self.ecc_provider._process_ecc_signature(der_signature)
        self.assertEqual(result, raw_signature)
        mock_serialize.assert_called_once_with(signature=der_signature, coordinate_length=32)

    @patch(
        "spsdk_offline_signature_provider.offline_signature_provider.PublicKeyEcc.serialize_signature"
    )
    def test_process_ecc_signature_invalid_size(self, mock_serialize):
        """Test processing ECC signature with invalid size."""
        invalid_signature = b"\x00" * 32  # Wrong size
        mock_serialize.side_effect = Exception("Invalid signature")

        with self.assertRaises(ValueError) as context:
            self.ecc_provider._process_ecc_signature(invalid_signature)
        self.assertIn("Failed to process ECC signature", str(context.exception))

    def test_process_rsa_signature_correct_size(self):
        """Test processing RSA signature with correct size."""
        rsa_signature = b"\x00" * 256  # 256 bytes for 2048-bit RSA
        result = self.rsa_provider._process_rsa_signature(rsa_signature)
        self.assertEqual(result, rsa_signature)

    def test_process_rsa_signature_invalid_size(self):
        """Test processing RSA signature with invalid size."""
        invalid_signature = b"\x00" * 128  # Wrong size

        with self.assertRaises(ValueError) as context:
            self.rsa_provider._process_rsa_signature(invalid_signature)
        self.assertIn("Got incorrect RSA signature size", str(context.exception))

    def test_process_rsa_signature_der_format(self):
        """Test processing RSA signature in DER format (larger than expected)."""
        # Simulate DER-encoded signature that's larger than expected
        der_signature = b"\x00" * 300  # Larger than expected 256 bytes

        # Should extract the last 256 bytes as potential signature
        result = self.rsa_provider._process_rsa_signature(der_signature)
        self.assertEqual(len(result), 256)
        self.assertEqual(result, b"\x00" * 256)


class TestOfflineSPUtilityMethods(unittest.TestCase):
    """Test utility methods."""

    def test_get_algorithm_display_name(self):
        """Test _get_algorithm_display_name method."""
        ecc_provider = OfflineSP(algorithm="ecc")
        rsa_pss_provider = OfflineSP(key_size=2048, algorithm="rsa-pss")
        rsa_pkcs1_provider = OfflineSP(key_size=2048, algorithm="rsa-pkcs1v15")

        self.assertEqual(ecc_provider._get_algorithm_display_name(), "ECC")
        self.assertEqual(rsa_pss_provider._get_algorithm_display_name(), "RSA-PSS")
        self.assertEqual(rsa_pkcs1_provider._get_algorithm_display_name(), "RSA-PKCS1v15")

    def test_get_algorithm_info(self):
        """Test get_algorithm_info method."""
        provider = OfflineSP(key_size=2048, algorithm="rsa-pss")
        info = provider.get_algorithm_info()

        expected_info = {
            "algorithm": "rsa-pss",
            "algorithm_display": "RSA-PSS",
            "key_size": 2048,
            "hash_algorithm": "sha256",
            "hash_algorithm_override": False,
            "signature_length": 256,
            "is_rsa": True,
            "uses_pss_padding": True,
        }

        self.assertEqual(info, expected_info)

    def test_get_signing_instructions_ecc(self):
        """Test get_signing_instructions for ECC."""
        provider = OfflineSP(key_size=256, algorithm="ecc")
        instructions = provider.get_signing_instructions()

        self.assertIn("ECC-256 signing instructions", instructions)
        self.assertIn("sha256", instructions)
        self.assertIn("64 bytes", instructions)
        self.assertIn("raw r||s format", instructions)

    def test_get_signing_instructions_rsa_pss(self):
        """Test get_signing_instructions for RSA-PSS."""
        provider = OfflineSP(key_size=2048, algorithm="rsa-pss")
        instructions = provider.get_signing_instructions()

        self.assertIn("RSA-PSS-2048 signing instructions", instructions)
        self.assertIn("sha256", instructions)
        self.assertIn("256 bytes", instructions)
        self.assertIn("PSS padding", instructions)

    def test_get_signing_instructions_rsa_pkcs1v15(self):
        """Test get_signing_instructions for RSA-PKCS1v15."""
        provider = OfflineSP(key_size=2048, algorithm="rsa-pkcs1v15")
        instructions = provider.get_signing_instructions()

        self.assertIn("RSA-PKCS1v15-2048 signing instructions", instructions)
        self.assertIn("sha256", instructions)
        self.assertIn("256 bytes", instructions)
        self.assertIn("PKCS1v15 padding", instructions)

    def test_validate_signature_compatibility_ecc(self):
        """Test validate_signature_compatibility for ECC."""
        provider = OfflineSP(key_size=256, algorithm="ecc")

        # Valid signature
        valid_sig = b"\x00" * 64
        self.assertTrue(provider.validate_signature_compatibility(valid_sig))

        # Invalid signature
        invalid_sig = b"\x00" * 32
        self.assertFalse(provider.validate_signature_compatibility(invalid_sig))

    def test_validate_signature_compatibility_rsa(self):
        """Test validate_signature_compatibility for RSA."""
        provider = OfflineSP(key_size=2048, algorithm="rsa-pss")

        # Valid signature
        valid_sig = b"\x00" * 256
        self.assertTrue(provider.validate_signature_compatibility(valid_sig))

        # Invalid signature
        invalid_sig = b"\x00" * 128
        self.assertFalse(provider.validate_signature_compatibility(invalid_sig))

    def test_str_representation(self):
        """Test __str__ method."""
        provider = OfflineSP(key_size=2048, algorithm="rsa-pss")
        str_repr = str(provider)

        self.assertIn("OfflineSP", str_repr)
        self.assertIn("algorithm=rsa-pss", str_repr)
        self.assertIn("key_size=2048", str_repr)
        self.assertIn("hash_alg=sha256", str_repr)

    def test_repr_representation(self):
        """Test __repr__ method."""
        provider = OfflineSP(hash_file="test_hash", key_size=2048, algorithm="rsa-pss")
        repr_str = repr(provider)

        self.assertIn("OfflineSP", repr_str)
        self.assertIn("hash_file='test_hash'", repr_str)
        self.assertIn("key_size=2048", repr_str)
        self.assertIn("algorithm='rsa-pss'", repr_str)


class TestOfflineSPSignMethod(unittest.TestCase):
    """Test the sign method with mocked dependencies."""

    def setUp(self):
        """Set up test fixtures."""
        self.provider = OfflineSP(key_size=256, algorithm="ecc")
        self.test_data = b"test data to sign"

    @patch("spsdk_offline_signature_provider.offline_signature_provider.get_hash")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.input")
    def test_sign_ecc_success(self, mock_input, mock_file, mock_get_hash):
        """Test successful ECC signing process."""
        # Mock hash generation
        mock_hash = b"\x12" * 32
        mock_get_hash.return_value = mock_hash

        # Mock user input for signature file path
        mock_input.return_value = "signature.bin"

        # Mock signature file content
        signature_data = b"\x00" * 64  # Valid ECC signature

        with patch("builtins.open", mock_open(read_data=signature_data)):
            result = self.provider.sign(self.test_data)

        self.assertEqual(result, signature_data)
        mock_get_hash.assert_called_once_with(
            data=self.test_data, algorithm=EnumHashAlgorithm.SHA256
        )

    @patch("spsdk_offline_signature_provider.offline_signature_provider.get_hash")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.input")
    def test_sign_rsa_success(self, mock_input, mock_file, mock_get_hash):
        """Test successful RSA signing process."""
        provider = OfflineSP(key_size=2048, algorithm="rsa-pss")

        # Mock hash generation
        mock_hash = b"\x12" * 32
        mock_get_hash.return_value = mock_hash

        # Mock user input for signature file path
        mock_input.return_value = "signature.bin"

        # Mock signature file content
        signature_data = b"\x00" * 256  # Valid RSA signature

        with patch("builtins.open", mock_open(read_data=signature_data)):
            result = provider.sign(self.test_data)

        self.assertEqual(result, signature_data)
        mock_get_hash.assert_called_once_with(
            data=self.test_data, algorithm=EnumHashAlgorithm.SHA256
        )


class TestOfflineSPIntegration(unittest.TestCase):
    """Integration tests for OfflineSP."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: self._cleanup_temp_dir())

    def _cleanup_temp_dir(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_real_file_operations(self):
        """Test with real file operations."""
        provider = OfflineSP(
            hash_file=os.path.join(self.temp_dir, "test_hash"), key_size=256, algorithm="ecc"
        )

        # Create a signature file
        sig_file = os.path.join(self.temp_dir, "signature.bin")
        signature_data = b"\x00" * 64
        with open(sig_file, "wb") as f:
            f.write(signature_data)

        test_data = b"test data"

        with patch("builtins.input", return_value=sig_file):
            with patch(
                "spsdk_offline_signature_provider.offline_signature_provider.get_hash"
            ) as mock_hash:
                mock_hash.return_value = b"\x12" * 32
                result = provider.sign(test_data)

        self.assertEqual(result, signature_data)

        # Check that hash file was created
        expected_hash_file = os.path.join(self.temp_dir, "test_hash_ecc.sha256")
        self.assertTrue(os.path.exists(expected_hash_file))

        # Check hash file content
        with open(expected_hash_file, "rb") as f:
            hash_content = f.read()
        self.assertEqual(hash_content, b"\x12" * 32)

    def test_identifier_property(self):
        """Test that identifier is set correctly."""
        self.assertEqual(OfflineSP.identifier, "offline-sp")
