
J-Link Debug probe Plugin
=========================


* Free software: BSD-3-Clause


Features
--------

* Allow SPSDK to use J-Link as an interface for debugger probes.


Installation
------------

* Activate virtual env, where you have SPSDK
    - to install spsdk run: `pip install spsdk`
* `pip install spsdk-jlink`
* Verify installation by running `nxpdebugmbox --help`
    - you should see `jlink` amongst available interfaces (--interface)


Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [SPSDK Debug Probe project template](https://github.com/nxp-mcuxpresso/spsdk/blob/master/examples/plugins/templates/cookiecutter-spsdk-debug-probe-plugin.zip).
