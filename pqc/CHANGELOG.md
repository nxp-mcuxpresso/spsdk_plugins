
Change Log
==========

0.7.4 (2026-07-09)
------------------

* Upgraded codebase to utilize Python 3.10 features (PEP 604 union types, built-in generic types, `collections.abc` imports).

0.7.3 (2026-06-29)
------------------

* Add ML-DSA key migration tooling (`pqctool migrate-key`) for converting keys
  from legacy Dilithium formats.
* Improve migration compatibility to work even when native ML-DSA support is not
  available in the linked crypto backend.
* Mark ML-DSA key unions as `TypeAlias` for better typing compatibility.

0.7.2 (2026-06-03)
------------------

* Added Python 3.14 support.
* Dropped Python 3.9 support.

0.2.0 (2024-05-15)
------------------

* Move to Dilithium 3 with randomized signing

0.1.0 (2023-06-12)
------------------

* Dilithium 2 support
* Parameters: SHAKE-based matrix extension, Non-randomized signing
* Operations: generate key pair, sign data, verify signature
