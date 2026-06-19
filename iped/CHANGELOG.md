# Changelog

All notable changes to the spsdk-iped package will be documented in this file.

## [0.1.0] - 2026-05-27

### Added
- Initial release of the SPSDK IPED C++ PRINCE cipher backend
- CTR mode encryption/decryption with address-based counter
- GCM mode encryption/decryption with authentication tag support
- Double encryption mode (22 effective PRINCE rounds)
- Python wrapper using ctypes for the C++ shared library
- Auto-detection by SPSDK when installed (via `get_prince_cipher()`)
- Known-answer verification test on first use to ensure correctness
- ~100-150x speedup over pure-Python fallback

### Fixed
- Undefined behavior in C++ code causing incorrect results on ARM64
  (signed integer overflow and shift-width issues)
- Reference test vectors now pass on both x86_64 and ARM64
