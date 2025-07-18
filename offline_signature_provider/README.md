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

### Workflow

1. When SPSDK needs to sign data, it will call the Offline Signature Provider
2. The provider will:
   - Calculate the hash of the data
   - Print the hash value to the console
   - Save the hash to a file (e.g., `ahab_container_hash.SHA256`)
   - Prompt you to provide the path to a signature file
3. You can then:
   - Use your secure signing process to sign the hash
   - Provide the path to the signature file when prompted
4. The provider will:
   - Verify the signature format and size
   - Return the signature to SPSDK to complete the operation

### Supported Hash Algorithms

The hash algorithm is determined by the key size:

- 256-bit key: SHA-256
- 384-bit key: SHA-384
- 521-bit key: SHA-512

## Development

### Requirements

- Python 3.9+
- SPSDK 2.x

## License

This project is licensed under the BSD-3-Clause License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
