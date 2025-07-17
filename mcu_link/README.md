    SPSDK MCU-Link
    ==============

    NXP SPSDK MCU-Link debug probe support plugin for NXP LPC-Link/MCU-Link hardware debug probes. This plugin enables seamless integration with NXP's debug hardware.

    * Free software: BSD-3-Clause
    * Documentation: https://github.com/nxp-mcuxpresso/spsdk_plugins?tab=readme-ov-file#readme

    Features
    --------

    * Support for NXP MCU-Link debug probes
    * CMSIS-DAP protocol implementation
    * Firmware update capabilities
    * Debug session management
    * SWD/JTAG interface support
    * Integration with SPSDK tools

    Installation
    ------------

    1. Activate your virtual environment with SPSDK (to install spsdk run: `pip install spsdk`):

        python -m venv venv
        source venv/bin/activate  # On Windows: venv\Scripts\activate


    2. Install the package:

        pip install spsdk_mcu_link


    3. Verify installation:

        nxpdebugmbox --help

        You should see `mcu-link` listed among available interfaces (--interface)

    Usage
    -----

    1. Connect your MCU-Link debug probe to your computer
    2. Basic debug session:

        nxpdebugmbox --interface mcu-link --port auto

    3. For firmware updates:

        nxpdebugmbox update-firmware --interface mcu-link


    Advanced Usage
    -------------

    * Configuration options
    * Debugging commands
    * Firmware management
    * Troubleshooting tips

    Requirements
    -----------

    * Python 3.7 or newer
    * SPSDK package
    * USB drivers for MCU-Link hardware

    Contributing
    -----------

    Contributions are welcome! Please feel free to submit a Pull Request.

    Credits
    -------

    Michal Kelnar
    <michal.kelnar@nxp.com>

    License
    -------

    BSD-3-Clause
