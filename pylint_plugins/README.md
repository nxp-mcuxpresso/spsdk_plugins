
PyLint plugins covering SPSDK-specific coding rules
===================================================


* Free software: BSD-3-Clause


Features
--------

* `click-choice`: Check if click.Choice options are not case sensitive


Installation
------------

* Activate virtual env, meant for SPSDK development
* `pip install spsdk-pylint-plugins`
* add `spsdk-pylint-plugins` into `load-plugins` section of you PyLint config file (.pylintrc, pyproject.toml, etc.)
* run `pylint` as usual

Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [SPSDK Debug Probe project template](https://github.com/nxp-mcuxpresso/spsdk/blob/master/examples/plugins/templates/cookiecutter-spsdk-debug-probe-plugin.zip).
