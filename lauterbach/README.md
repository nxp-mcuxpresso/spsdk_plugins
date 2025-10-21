
Lauterbach debug probe Plugin
=============================


* Free software: BSD-3-Clause


Features
--------

* Allow SPSDK to use Trace32 as an interface for Lauterbach debugger probes.


Installation
------------

* Activate virtual env, where you have SPSDK
    - to install spsdk run: `pip install spsdk`
* `pip install spsdk-lauterbach`
* Verify installation by running `nxpdebugmbox --help`
    - you should see `lauterbach` amongst available interfaces (--interface)


Usage
-----

* Make sure to enable remote control to Trace32 in your config file
    ```
    <mandatory empty line>
    ; Remote Control Access
    RCL=NETTCP
    PORT=20000
    <mandatory empty line>
    ```

* Make sure your startup script contains the following:
  - (required) DEBUGPORTTYPE (SWD, JTAG, CJTAG)
  - (required) CPU family (e.g.: CortexM33)
  - (optional) exact CPU (e.g.: LPC55S69JBD64-CPU0)
    - Exact CPU is not crucial for Debug Authentication (DA), it's for testing whether DA was successful
    - Without specifying exact CPU, `nxpdebugmbox` will end `without AHB access`, thus unable to determine DA's status


* Start Trace32
* Run your startup script
* Run `nxpdebugmbox`
  - you may specify `-i/--interface lauterbach`
  - you may specify `-s/--serial-no <probe's serial number>`


Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage) project template.
