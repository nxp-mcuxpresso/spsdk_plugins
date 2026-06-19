# SPSDK IPED - PRINCE Cipher Backend

High-performance C++ PRINCE cipher backend for SPSDK's IPED
(Inline PRINCE Encryption/Decryption) module.

## Installation

### Prerequisites

A C++ compiler is required to build the native PRINCE cipher library:
- **Linux/macOS**: GCC or Clang (install via your package manager)
- **Windows**: MS Build Tools ([instructions](https://stackoverflow.com/questions/40504552/how-to-install-visual-c-build-tools))

### Install from source

```bash
pip install -e path/to/spsdk_plugins/iped
```

### Install from Bitbucket

```bash
pip install git+ssh://git@bitbucket.sw.nxp.com/spsdk/spsdk_plugins.git#subdirectory=iped
```

## Usage with SPSDK

When this package is installed, SPSDK's IPED module automatically detects the C++ backend
and uses it for ~100-150x faster PRINCE cipher operations compared to the built-in
pure-Python fallback.

No additional configuration is needed — just install the package alongside SPSDK.

## Standalone usage

```python
from spsdk_iped import IPED

# CTR mode encryption
cipher = IPED(key=0x01, address=0x80003000, iv=0x79EAFAB3A72412A1)
encrypted = cipher.encrypt(plaintext_bytes)

# Decryption
cipher2 = IPED(key=0x01, address=0x80003000, iv=0x79EAFAB3A72412A1)
decrypted = cipher2.decrypt(encrypted)
```

## Performance

The C++ backend provides approximately 100-150x speedup over the pure-Python implementation:

| Backend | Throughput |
|---------|-----------|
| Python (built-in) | ~0.03 MB/s |
| C++ (this package) | ~5 MB/s |

## License

BSD-3-Clause
