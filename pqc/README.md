
Post-Quantum Crypto plugin for SPSDK
====================================


* Free software: BSD-3-Clause


Features
--------

* Supported Algorithms:
    - Dilithium 2, 3, 5
    - ML-DSA 44, 65, 87
* Supported operation: Generate key pair, Sign data, Verify signature


Installation
------------

* Activate virtual env, where you have SPSDK
    - if SPSDK is not installed, the latest one will be installed automatically from [PyPI](https://pypi.org/project/spsdk/)
* `pip install spsdk-pqc`

Usage
-----

* Use tools such as nxpcrypto, nxpimage as you usually do.
* Plugin also comes with a cli app `pqctool`

Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [SPSDK Signature Provider project template](https://github.com/nxp-mcuxpresso/spsdk/blob/master/examples/plugins/templates/cookiecutter-spsdk-sp-plugin.zip).
