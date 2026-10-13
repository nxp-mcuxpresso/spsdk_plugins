Change Log
==========

0.3.12 (2026-10-01)
-------------------

* Import `DebugProbeCoreSightOnly` from `spsdk.debuggers.debug_probe_arm` (no longer re-exported from `spsdk.debuggers.debug_probe` in newer SPSDK), with a fallback for SPSDK 3.10.

0.3.11 (2026-09-15)
-------------------

* Declared ADIv6 (CoreSight 600 / DPv3) support at the shared SPSDK base class level via `SUPPORTED_VERSIONS`.

0.3.10 (2026-09-02)
-------------------

* Added ARM ADIv6 (CoreSight 600 / DPv3) support by removing the ADIv5-only AP SELECT override so the probe inherits the ADIv6-aware AP addressing (memory-mapped AP base address and SELECT1 for 64-bit address spaces) from SPSDK.

0.3.9 (2026-08-20)
------------------

* Fixed debug port initialization and recovery ordering for J-Link connections.

0.3.8 (2026-08-12)
------------------

* Unified CoreSight transaction TRACE output and added a DPIDR read after connection setup.

0.3.7 (2026-07-21)
------------------

* Added JTAG debug protocol support.

0.3.6 (2026-07-09)
------------------

* Upgraded codebase to utilize Python 3.10 features (PEP 604 union types, built-in generic types, `collections.abc` imports).

0.3.5 (2026-06-03)
------------------

* Added Python 3.14 support.
* Dropped Python 3.9 support.

0.3.4 (2026-05-18)
------------------

* Added CoreSight access port selection support for J-Link probe AP register access.

0.1.0 (2024-04-26)
------------------

* First release on PyPI.
