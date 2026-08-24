Change Log
==========

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
