#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Wrapper for Open-Quantum-Safe python library."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from typing_extensions import Self

from . import pqc_asn
from .errors import PQCError
from .liboqs_oqs import Signature

logger = logging.getLogger(__name__)

DISABLE_DIL_MLDSA_PUBLIC_KEY_MISMATCH_WARNING = False


class PQCAlgorithm(str, Enum):
    """Supported PQC algorithms."""

    DILITHIUM2 = "Dilithium2"
    DILITHIUM3 = "Dilithium3"
    DILITHIUM5 = "Dilithium5"
    ML_DSA_44 = "ML-DSA-44"
    ML_DSA_65 = "ML-DSA-65"
    ML_DSA_87 = "ML-DSA-87"


DILITHIUM_GROUP_OID = "1.3.6.1.4.1.2.267.7"
DILITHIUM_ALGORITHMS = [
    PQCAlgorithm.DILITHIUM2,
    PQCAlgorithm.DILITHIUM3,
    PQCAlgorithm.DILITHIUM5,
]
DILITHIUM_LEVEL = {
    2: PQCAlgorithm.DILITHIUM2,
    3: PQCAlgorithm.DILITHIUM3,
    5: PQCAlgorithm.DILITHIUM5,
}

ML_DSA_GROUP_OID = "2.16.840.1.101.3.4.3"
ML_DSA_ALGORITHMS = [
    PQCAlgorithm.ML_DSA_44,
    PQCAlgorithm.ML_DSA_65,
    PQCAlgorithm.ML_DSA_87,
]
ML_DSA_LEVEL = {
    2: PQCAlgorithm.ML_DSA_44,
    3: PQCAlgorithm.ML_DSA_65,
    5: PQCAlgorithm.ML_DSA_87,
}


@dataclass
class KeyInfo:
    """PQC Key information class."""

    level: int
    private_key_size: int
    public_key_size: int
    signature_size: int
    oid: str

    @property
    def data_size(self) -> int:
        """Raw key data size."""
        return self.private_key_size + self.public_key_size


KEY_INFO = {
    PQCAlgorithm.DILITHIUM2: KeyInfo(
        level=2,
        private_key_size=2528,
        public_key_size=1312,
        signature_size=2420,
        oid=DILITHIUM_GROUP_OID + ".4.4",
    ),
    PQCAlgorithm.DILITHIUM3: KeyInfo(
        level=3,
        private_key_size=4000,
        public_key_size=1952,
        signature_size=3293,
        oid=DILITHIUM_GROUP_OID + ".6.5",
    ),
    PQCAlgorithm.DILITHIUM5: KeyInfo(
        level=5,
        private_key_size=4864,
        public_key_size=2592,
        signature_size=4595,
        oid=DILITHIUM_GROUP_OID + ".8.7",
    ),
    PQCAlgorithm.ML_DSA_44: KeyInfo(
        level=2,
        private_key_size=2560,
        public_key_size=1312,
        signature_size=2420,
        oid=ML_DSA_GROUP_OID + ".17",
    ),
    PQCAlgorithm.ML_DSA_65: KeyInfo(
        level=3,
        private_key_size=4032,
        public_key_size=1952,
        signature_size=3309,
        oid=ML_DSA_GROUP_OID + ".18",
    ),
    PQCAlgorithm.ML_DSA_87: KeyInfo(
        level=5,
        private_key_size=4896,
        public_key_size=2592,
        signature_size=4627,
        oid=ML_DSA_GROUP_OID + ".19",
    ),
}


class PQCKey:
    """Base class for all supported PQC keys."""

    ALGORITHMS: list[PQCAlgorithm] = []

    def __init__(self, algorithm: PQCAlgorithm):
        """Initialize PQC key with given algorithm."""
        if algorithm not in self.ALGORITHMS:
            raise PQCError(
                f"Algorithm {algorithm} is not allowed in class {self.__class__.__name__}"
            )
        self.algorithm = algorithm
        self.key_info = KEY_INFO[self.algorithm]

    @property
    def signature_size(self) -> int:
        """Size of signature data."""
        return KEY_INFO[self.algorithm].signature_size

    @property
    def level(self) -> int:
        """NIST claim level."""
        return KEY_INFO[self.algorithm].level


class PQCPublicKey(PQCKey):
    """Base class for all supported PQC public keys."""

    ALGORITHMS = DILITHIUM_ALGORITHMS + ML_DSA_ALGORITHMS

    def __init__(self, public_data: bytes) -> None:
        """Initialize PQC public key."""
        for alg in self.ALGORITHMS:
            if len(public_data) == KEY_INFO[alg].public_key_size:
                super().__init__(algorithm=alg)
                self.public_data = public_data
                break
        else:
            raise PQCError(f"Invalid data size {len(public_data)} for {self.__class__.__name__}")

    def verify(self, signature: bytes, data: bytes) -> bool:
        """Verify signature."""
        with Signature(alg_name=self.algorithm.value) as sig:
            result = sig.verify(message=data, signature=signature, public_key=self.public_data)
        return result

    def export(self, pem: bool = True) -> bytes:
        """Export key in PEM or DER format."""
        return pqc_asn.encode_puk(
            data=self.public_data,
            oid=self.key_info.oid,
            pem=pem,
            algorithm_name=self.algorithm.value,
        )

    @classmethod
    def parse(cls, data: bytes) -> Self:
        """Create key from raw or PEM/DER encoded data."""
        try:
            key = cls(public_data=data)
            logger_func = (
                logger.debug if DISABLE_DIL_MLDSA_PUBLIC_KEY_MISMATCH_WARNING else logger.warning
            )
            logger_func(
                "Parsing raw public key data. Key type (Dilithium/ML-DSA) might be incorrect."
            )

            return key
        except PQCError:
            pass
        oid, data = pqc_asn.decode_puk(data=data)
        if oid.startswith(DILITHIUM_GROUP_OID):
            return DilithiumPublicKey(public_data=data)  # type: ignore[return-value]
        if oid.startswith(ML_DSA_GROUP_OID):
            return MLDSAPublicKey(public_data=data)  # type: ignore[return-value]
        raise PQCError("Unable to determine PQC Public key type (Dilithium/ML-DSA)")

    @property
    def key_size(self) -> int:
        """Key size in bits."""
        return KEY_INFO[self.algorithm].public_key_size * 8


class PQCPrivateKey(PQCKey):
    """Base class for all supported PQC private keys."""

    ALGORITHMS = DILITHIUM_ALGORITHMS + ML_DSA_ALGORITHMS

    def __init__(
        self, algorithm: Optional[PQCAlgorithm] = None, data: Optional[bytes] = None
    ) -> None:
        """Initialize PQC private key."""
        if data is None:
            if algorithm is None:
                raise PQCError("You must provide either 'data' or 'algorithm'")
            if isinstance(algorithm, str):
                algorithm = PQCAlgorithm(algorithm)
            assert isinstance(algorithm, PQCAlgorithm)
            with Signature(alg_name=algorithm.value) as sig:
                super().__init__(algorithm=algorithm)
                self.public_data = sig.generate_keypair()
                self.private_data = sig.export_secret_key()
        else:
            for alg in self.ALGORITHMS:
                if len(data) in [KEY_INFO[alg].private_key_size, KEY_INFO[alg].data_size]:
                    super().__init__(algorithm=alg)
                    self.private_data = data[: KEY_INFO[alg].private_key_size]
                    self.public_data = None
                    break
            else:
                raise PQCError(f"Invalid data size {len(data)} for {self.__class__.__name__}")

    def sign(self, data: bytes) -> bytes:
        """Sign data."""
        with Signature(alg_name=self.algorithm.value, secret_key=self.private_data) as sig:
            signature = sig.sign(data)
        return signature

    def verify(self, signature: bytes, data: bytes) -> bool:
        """Verify signature."""
        with Signature(alg_name=self.algorithm.value) as sig:
            result = sig.verify(message=data, signature=signature, public_key=self.public_data)
        return result

    def export(self, pem: bool = True) -> bytes:
        """Export key in PEM or DER format."""
        data = self.private_data + self.public_data
        return pqc_asn.encode_prk(
            data=data,
            oid=self.key_info.oid,
            pem=pem,
            algorithm_name=self.algorithm.value,
        )

    def get_public_key(self) -> PQCPublicKey:
        """Create an instance of public key."""
        return PQCPublicKey(public_data=self.public_data)

    @classmethod
    def parse(cls, data: bytes) -> Self:
        """Create key from raw or PEM/DER encoded data."""
        try:
            return cls(data=data)
        except PQCError:
            pass
        # we don't care about the oid, as each private key has different length
        _oid, data = pqc_asn.decode_prk(data=data)
        return cls(data=data)

    @property
    def key_size(self) -> int:
        """Key size in bits."""
        return KEY_INFO[self.algorithm].private_key_size * 8


class DilithiumPrivateKey(PQCPrivateKey):
    """Dilithium Private Key."""

    ALGORITHMS = DILITHIUM_ALGORITHMS

    def __init__(
        self,
        level: Optional[int] = None,
        algorithm: Optional[PQCAlgorithm] = None,
        data: Optional[bytes] = None,
    ):
        """Initialize Dilithium private key."""
        if not data:
            if level:
                algorithm = DILITHIUM_LEVEL.get(level)
            if not algorithm:
                raise PQCError("PQC Algorithm must be specified either by 'level' or 'algorithm'")
        super().__init__(algorithm, data)


class DilithiumPublicKey(PQCPublicKey):
    """Dilithium Public Key."""

    ALGORITHMS = DILITHIUM_ALGORITHMS


class MLDSAPrivateKey(PQCPrivateKey):
    """ML-DSA Private Key."""

    ALGORITHMS = ML_DSA_ALGORITHMS

    def __init__(
        self,
        level: Optional[int] = None,
        algorithm: Optional[PQCAlgorithm] = None,
        data: Optional[bytes] = None,
    ):
        """Initialize ML-DSA private key."""
        if not data:
            if level:
                algorithm = ML_DSA_LEVEL.get(level)
            if not algorithm:
                raise PQCError("PQC Algorithm must be specified either by 'level' or 'algorithm'")
        super().__init__(algorithm, data)


class MLDSAPublicKey(PQCPublicKey):
    """ML-DSA Public Key."""

    ALGORITHMS = ML_DSA_ALGORITHMS
