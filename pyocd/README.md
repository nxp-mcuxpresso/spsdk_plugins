
PyOCD SW Debugger
=================


* Free software: BSD-3-Clause


Features
--------

* Allow SPSDK to use PyOCD as an interface for debugger probes.


Installation
------------

* Activate virtual env, where you have SPSDK
    - to install spsdk run: `pip install spsdk`
* Install the package
    - `pip install spsdk-pyocd`
* If you want to use P&E Micro debugger probes install the `pemicro` extra
    - `pip install spsdk-pyocd[pemicro]`

* Verify installation by running `nxpdebugmbox --help`
    - you should see `pyocd` amongst available interfaces (--interface)


Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [SPSDK Debug Probe project template](https://github.com/nxp-mcuxpresso/spsdk/blob/master/examples/plugins/templates/cookiecutter-spsdk-debug-probe-plugin.zip).
