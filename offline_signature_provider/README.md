# Offline Signature Provider for SPSDK

A plugin for SPSDK that provides an offline signature provider for secure boot workflows.

## Overview

The Offline Signature Provider allows you to sign data without having the private key directly accessible to the SPSDK tool. Instead, it:

1. Calculates the hash of the data to be signed
2. Writes the hash to a file
3. Waits for you to provide a signature file (which you can generate using your secure signing process)
4. Verifies and uses the provided signature

This workflow is particularly useful for high-security environments where private keys must be kept in secure hardware or air-gapped systems.

## Installation

```bash
pip install spsdk-offline-signature-provider
```

## Configuration

The Offline Signature Provider can be configured with the following options:

### Supported Algorithms

- **ECC** (`ecc`): Elliptic Curve Cryptography
- **RSA-PSS** (`rsa-pss`): RSA with PSS padding
- **RSA-PKCS1v15** (`rsa-pkcs1v15`): RSA with PKCS#1 v1.5 padding

### Supported Key Sizes

#### ECC Key Sizes
- **256 bits**: Default SHA-256 hash algorithm, 64-byte signature
- **384 bits**: Default SHA-384 hash algorithm, 96-byte signature
- **521 bits**: Default SHA-512 hash algorithm, 132-byte signature

#### RSA Key Sizes
- **2048 bits**: Default SHA-256 hash algorithm, 256-byte signature
- **3072 bits**: Default SHA-256 hash algorithm, 384-byte signature
- **4096 bits**: Default SHA-256 hash algorithm, 512-byte signature

### Supported Hash Algorithms

You can override the default hash algorithm by specifying one of:
- **SHA-256** (`sha256`): 256-bit hash
- **SHA-384** (`sha384`): 384-bit hash
- **SHA-512** (`sha512`): 512-bit hash
- **SHA-1** (`sha1`): 160-bit hash (legacy, not recommended for new applications)

### Configuration Parameters

When configuring the offline signature provider in your SPSDK configuration file, you can specify:

- `hash_file`: Base name for the hash file (default: `"hash_file"`)
- `key_size`: Size of the key in bits (default: `"256"`)
- `algorithm`: Signature algorithm to use (default: `"ecc"`)
- `hash_algorithm`: Hash algorithm to use (optional, uses algorithm/key-size defaults if not specified)

### Example Configurations

#### Basic Configuration (using defaults)
```yaml
# SPSDK configuration file example
signer: type=offline-sp;algorithm=ecc;key_size=256
```

#### Advanced Configuration with Custom Hash Algorithm
```yaml
# SPSDK configuration file example with custom hash
signer: type=offline-sp;algorithm=rsa-pss;key_size=2048;hash_algorithm=sha384
```

#### Configuration with Custom Hash File Name
```yaml
# SPSDK configuration file example with custom hash file
signer: type=offline-sp;hash_file=my_container_hash;algorithm=ecc;key_size=384
```

### Hash File Naming

The provider automatically creates algorithm-specific hash file names:
- Format: `{hash_file}_{algorithm}.{hash_algorithm}`
- Examples:
  - `hash_file_ecc.SHA256` (ECC-256 with default SHA-256)
  - `hash_file_rsa-pss.SHA384` (RSA-PSS-2048 with custom SHA-384)
  - `my_container_hash_ecc.SHA384` (ECC-384 with custom hash file name)

### Default Hash Algorithm Behavior

If no `hash_algorithm` is specified, the provider uses these defaults:

#### ECC Defaults
- 256-bit key: SHA-256
- 384-bit key: SHA-384
- 521-bit key: SHA-512

#### RSA Defaults (both PSS and PKCS1v15)
- 2048-bit key: SHA-256
- 3072-bit key: SHA-256
- 4096-bit key: SHA-256

### Workflow

1. When SPSDK needs to sign data, it will call the Offline Signature Provider
2. The provider will:
   - Calculate the hash of the data using the configured hash algorithm
   - Print the hash value to the console
   - Save the hash to a file (e.g., `hash_file_ecc.SHA256`)
   - Display algorithm-specific signing instructions
   - Indicate whether using default or custom hash algorithm
   - Prompt you to provide the path to a signature file
3. You can then:
   - Use your secure signing process to sign the hash according to the displayed instructions
   - Provide the path to the signature file when prompted
4. The provider will:
   - Validate the signature format and size
   - Process the signature according to the algorithm (handle DER encoding if needed)
   - Return the signature to SPSDK to complete the operation

### Algorithm-Specific Instructions

#### ECC Signing
- Use the provided hash with your ECC private key
- Signature can be in raw r||s format or DER-encoded format
- The provider will automatically convert DER-encoded signatures to raw format

#### RSA-PSS Signing
- Use the provided hash with your RSA private key and PSS padding
- Use the specified hash algorithm with PSS padding
- Salt length should equal digest length
- Provide signature as raw bytes

#### RSA-PKCS1v15 Signing
- Use the provided hash with your RSA private key and PKCS#1 v1.5 padding
- Use the specified hash algorithm with PKCS#1 v1.5 padding
- Provide signature as raw bytes

### Hash Algorithm Override Examples

#### Using SHA-384 with ECC-256 (instead of default SHA-256)
```yaml
signer: type=offline-sp;algorithm=ecc;key_size=256;hash_algorithm=sha384
```

#### Using SHA-512 with RSA-PSS-2048 (instead of default SHA-256)
```yaml
signer: type=offline-sp;algorithm=rsa-pss;key_size=2048;hash_algorithm=sha512
```

### Requirements

- Python 3.9+
- SPSDK 3.x

### Provider Identifier

The provider uses the identifier `offline-sp` in SPSDK configuration files.

## License

This project is licensed under the BSD-3-Clause License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
