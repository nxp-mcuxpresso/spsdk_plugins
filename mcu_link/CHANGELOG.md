Change Log
==========

0.6.18 (2026-10-01)
-------------------

* Skip USB devices with unreadable descriptors (pyusb ValueError "no langid" or USBError) during probe enumeration instead of aborting the discovery of all debug probes.
* Import `DebugProbeCoreSightOnly` from `spsdk.debuggers.debug_probe_arm` (no longer re-exported from `spsdk.debuggers.debug_probe` in newer SPSDK), with a fallback for SPSDK 3.10.

0.6.17 (2026-09-25)
-------------------

* Fixed on-board MCU-Link CMSIS-DAP probe detection by providing a PyInstaller hidden import hint for `libusb_package`.

0.6.16 (2026-09-15)
-------------------

* Declared ADIv6 (CoreSight 600 / DPv3) support at the shared SPSDK base class level via `SUPPORTED_VERSIONS`.

0.6.15 (2026-09-02)
-------------------

* Added ADIv6 (CoreSight 600 / DPv3) support by delegating AP SELECT/SELECT1 handling to the ADIv6-aware SPSDK base class.
* Standardized CoreSight AP access with other probes (J-Link, PyOCD); the WebixDapper WASM backend no longer owns AP SELECT internally.

0.6.14 (2026-08-12)
-------------------

* Unified CoreSight transaction TRACE output and added a DPIDR read after connection setup.

0.6.13 (2026-07-21)
-------------------

* Added SWD/JTAG debug probe protocol selection for MCU-Link.
* Refreshed the bundled WebixDapper WASM backend with `connect(useJTAG)` support.

0.6.12 (2026-07-09)
-------------------

* Upgraded codebase to utilize Python 3.10 features (PEP 604 union types, built-in generic types, `collections.abc` imports).

0.6.11 (2026-06-03)
-------------------

* Added Python 3.14 support.
* Dropped Python 3.9 support.
* Reverted the MCU-Link USB backend packaging from libusb-package-tng back to libusb-package.

0.6.10 (2026-06-03)
-------------------

* Switched the MCU-Link USB backend packaging from libusb-package to libusb-package-tng.
* Updated USB interface discovery to use a shared PyUSB libusb backend helper.
* Added Python 3.14 classifier support.

0.6.9 (2026-05-21)
------------------

* Fixed MCU-Link target connection sequence by powering up system and debug domains together.
* Added one probe interface reopen retry for transient connect failures.

0.6.3 (2025-03-06)
------------------

* Added possibility to filter probes by its serial numbers

0.6.2 (2024-11-22)
------------------

* Ready for public release


0.3.0 (2024-11-22)
------------------

* Fixed some bugs during reopen plugin
* Rename from Dapper to mcu-link.

0.2.0 (2024-11-12)
------------------

* Update the plugin to support LPC-link.

0.1.0 (2024-10-15)
------------------

* First release on PyPI.
