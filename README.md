# SPSDK Plugins

SPSDK allows users to install additional plugins that integrate with and extend SPSDK's core functionality. These plugins enable specialized features while keeping the core codebase clean and focused.

## Overview

The SPSDK plugins repository contains various extension modules that enhance SPSDK capabilities through a modular architecture. Each plugin follows standardized interfaces and provides specific functionality like debug probe support, cryptographic operations.

**Repository:** https://github.com/nxp-mcuxpresso/spsdk_plugins  
**PyPI Packages:** All plugins are available on PyPI
**License:** BSD-3-Clause

## Available Plugins

| Plugin | Description | Installation | License |
|--------|-------------|--------------|---------|
| **PyOCD** | Debug probe support via PyOCD | `pip install spsdk-pyocd` | BSD-3-Clause |
| **J-Link** | Debug probe support using PyLink library | `pip install spsdk-jlink` | BSD-3-Clause |
| **MCU-Link** | Support for NXP MCU-Link debug probes | Included with SPSDK by default | BSD-3-Clause |
| **PE Micro** | PE Micro debugger probe integration | `pip install spsdk-pemicro` | BSD-3-Clause |
| **Lauterbach** | Lauterbach debug probe support | `pip install spsdk-lauterbach` | BSD-3-Clause |
| **PKCS11** | PKCS#11 signature provider | `pip install spsdk-pkcs11` | BSD-3-Clause |
| **PQC** | Post-Quantum Cryptography support | `pip install spsdk-pqc` | BSD-3-Clause |
| **Keyfactor** | Keyfactor integration | `pip install spsdk-keyfactor` | BSD-3-Clause |
| **PyLint Plugins** | SPSDK-specific coding rules for PyLint | `pip install spsdk-pylint-plugins` | BSD-3-Clause |
| **Offline Signature Provider** | Offline signature provider| `pip install spsdk-offline-signature-provider` | BSD-3-Clause |

## Quick Start

1. Install SPSDK if not already installed:
```bash
pip install spsdk
```

2. Install desired plugin:
```bash
pip install spsdk-<plugin-name>
```

3. Verify installation:
```bash
nxpdebugmbox --help  # For debug probes
```

## Installation Verification

After installing a plugin, you can verify it's properly integrated:

- For debug probes: `nxpdebugmbox --help` (check available interfaces)
- For signature providers: Use `SignatureProvider.get_all_signature_providers()` method in your code
- For PyLint plugins: ensure they appear in your PyLint configuration

## New Plugin Implementation

Plugins installed in the Python environment are automatically discovered through entry points. SPSDK uses Python's entry points mechanism to detect and load plugins at runtime. The recommended approach is to use cookiecutter templates which provide a standardized structure and boilerplate code for new plugins.

### Supported Plugin Types

| Plugin Type | Entrypoint | Template Name | Base Class |
|-------------|------------|--------------|------------|
| Signature Provider | spsdk.sp | cookiecutter-spsdk-sp-plugin.zip | spsdk.crypto.signature_provider.SignatureProvider |
| Mboot Device Interface | spsdk.device.interface | cookiecutter-spsdk-device-interface-plugin.zip | spsdk.mboot.protocol.base.MbootProtocolBase |
| SDP Device Interface | spsdk.device.interface | cookiecutter-spsdk-device-interface-plugin.zip | spsdk.sdp.protocol.base.SDPProtocolBase |
| WPC Service | spsdk.wpc.service | cookiecutter-spsdk-wpc-service-plugin.zip | spsdk.wpc.utils.WPCCertificateService |
| Debug Probe | spsdk.debug_probe | cookiecutter-spsdk-debug-probe-plugin.zip | spsdk.debuggers.debug_probe.DebugProbeCoreSightOnly |


### Development Setup

1. Install development tools:
```bash
pip install cookiecutter
```

2. Choose the appropriate template based on your plugin type from the table above:
```bash
cookiecutter <spsdk_root>/examples/plugins/templates/<plugin_template>.zip
```

3. Follow the interactive prompts to configure your plugin such as:
   - Package name
   - Author information
   - Plugin description
   - Dependencies
   - Python version support

4. Implement your plugin functionality:
   - Modify the generated code skeleton
   - Add your custom implementation
   - Override required methods from the base class
   - Add any additional features needed

5. Install your plugin:
```bash
pip install -e <my_project_path>
```

### Best Practices
- Follow the base class interface for your plugin type
- Follow SPSDK coding standards

## Codecheck

This repository also includes the *codecheck* tool - a collection of quality checking tools for NXP Python projects. This standalone tool can verify code quality for any Python project and is used in SPSDK's CI/CD pipeline.