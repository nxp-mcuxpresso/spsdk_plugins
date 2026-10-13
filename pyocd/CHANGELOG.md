Change Log
==========

0.3.12 (2026-10-01)
-------------------

* Import `DebugProbeCoreSightOnly` from `spsdk.debuggers.debug_probe_arm` (no longer re-exported from `spsdk.debuggers.debug_probe` in newer SPSDK), with a fallback for SPSDK 3.10.

0.3.11 (2026-09-15)
-------------------

* Declared ADIv6 (CoreSight 600 / DPv3) support at the shared SPSDK base class level
  (via `SUPPORTED_VERSIONS`). Works through pyOCD backends where SPSDK's `select_ap()`
  owns DP SELECT/SELECT1, i.e. J-Link and CMSIS-DAP/MCU-Link.

0.3.10 (2026-08-12)
-------------------

* Unified CoreSight transaction TRACE output and added a DPIDR read after connection setup.

0.3.9 (2026-07-21)
------------------

* Added JTAG debug protocol support.

0.3.8 (2026-07-09)
------------------

* Upgraded codebase to utilize Python 3.10 features (PEP 604 union types, built-in generic types, `collections.abc` imports).

0.3.7 (2026-06-03)
------------------

* Added Python 3.14 support.
* Dropped Python 3.9 support.

0.3.6 (2026-05)
------------------

* Fixed J-Link MCU-Link probe not being found when using newer J-Link DLL versions (e.g. from LinkServer 26.3)

0.3.4 (2025-11)
------------------

* Updated PyOCD package dependency range to support versions up to 0.50


0.1.0 (2024-04-26)
------------------

* First release on PyPI.
