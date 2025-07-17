
P&E Micro debugger probe plugin
===============================


* Free software: BSD-3-Clause


Features
--------

* Allow SPSDK to use P&E Micro as an interface for debugger probes.


Installation
------------

* Activate virtual env, where you have SPSDK
    - to install spsdk run: `pip install spsdk`
* `pip install spsdk-pemicro`
* Verify installation by running `nxpdebugmbox --help`
    - you should see `pemicro` amongst available interfaces (--interface)


Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [SPSDK Debug Probe project template](https://github.com/nxp-mcuxpresso/spsdk/blob/master/examples/plugins/templates/cookiecutter-spsdk-debug-probe-plugin.zip).
