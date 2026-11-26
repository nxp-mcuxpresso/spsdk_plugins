Change Log
==========

0.5.10 (2026-10-20)
-------------------

* Removed the DPIDR read from `connect()`: Trace32 reports a bus error for a raw DP register read on some locked targets (e.g. i.MX95 before debug authentication), which broke `get-uuid` and debug authentication. Newer SPSDK reads DPIDR after connect itself and falls back to ADIv5 if the read fails.
* `close()` no longer raises when Trace32 stops responding after a target reset, and a remote API timeout while asserting the reset line re-opens the Trace32 connection instead of failing a successful debug authentication.

0.5.9 (2026-10-01)
------------------

* Import `DebugProbeCoreSightOnly` from `spsdk.debuggers.debug_probe_arm` (no longer re-exported from `spsdk.debuggers.debug_probe` in newer SPSDK), with a fallback for SPSDK 3.10.

0.5.8 (2026-09-15)
------------------

* Declared ADIv5-only support at the shared SPSDK base class level via `SUPPORTED_VERSIONS`; the base class now rejects ADIv6 targets before reaching this probe, so the local `_get_cs_addr` ADIv6 branch was removed as redundant.

0.5.7 (2026-09-02)
------------------

* Detect ARM ADIv6 (CoreSight 600 / DPv3) targets and encode only the A[3:2] wire bits for Access Port access, leaving DP SELECT/SELECT1 to the SPSDK base class. Experimental and not verified on hardware, as the T32 "EDBG:" access class is undocumented.

0.5.6 (2026-08-12)
------------------

* Unified CoreSight transaction TRACE output and added a DPIDR read after connection setup.

0.5.4 (2026-07-09)
------------------

* Upgraded codebase to utilize Python 3.10 features (PEP 604 union types, built-in generic types, `collections.abc` imports).

0.5.3 (2026-06-03)
------------------

* Added Python 3.14 support.
* Dropped Python 3.9 support.

0.1.0 (2024-04-24)
------------------

* CoreSight access (via DAP)
* Memory access (via DAP)
