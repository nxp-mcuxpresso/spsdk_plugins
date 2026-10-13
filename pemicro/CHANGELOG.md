Change Log
==========

0.3.12 (2026-10-01)
-------------------

* Import `DebugProbeCoreSightOnly` from `spsdk.debuggers.debug_probe_arm` (no longer re-exported from `spsdk.debuggers.debug_probe` in newer SPSDK), with a fallback for SPSDK 3.10.

0.3.11 (2026-09-15)
-------------------

* Declared ADIv5-only support at the shared SPSDK base class level via `SUPPORTED_VERSIONS`; the base class now rejects ADIv6 targets before reaching this probe, so the local `_get_ap_index` ADIv6 check was removed as redundant.

0.3.10 (2026-09-07)
-------------------

* Detect ARM ADIv6 (CoreSight 600 / DPv3) targets and raise a clear error on Access Port access. The PyPEMicro DLL supports only APSEL index based Access Port access and cannot address memory-mapped ADIv6 Access Ports.

0.3.9 (2026-08-12)
------------------

* Unified CoreSight transaction TRACE output and added a DPIDR read after connection setup.

0.3.8 (2026-07-21)
------------------

* Added JTAG debug protocol support.

0.3.7 (2026-07-09)
------------------

* Upgraded codebase to utilize Python 3.10 features (PEP 604 union types, built-in generic types, `collections.abc` imports).

0.3.6 (2026-06-03)
------------------

* Added Python 3.14 support.
* Dropped Python 3.9 support.

0.1.0 (2024-04-26)
------------------

* First release on PyPI.
