
PKCS#11 Signature Provider
==========================

Signature Provider plugin for SPSDK using PKCS#11 interface


Features
--------

* Using a PKCS#11 library to sign data using HSM
* Supported signing schemes: RSA, RSA-PSS, ECDSA

Installation
------------

* Activate virtual env, where you have SPSDK
    - to install spsdk run: `pip install spsdk`
* `pip install spsdk-pkcs11`


Usage
-----

* To use this Signature Provider, you have to update your signature provider configuration string(s) in YAML file(s)
* Configuration string Parameters:
    - `type`: set to `pkcs11`
    - `so_path`: Path to (or name of) your PKCS#11 library (usually delivered by HSM vendor)
        - Plugin is looking for the library in current directory, and paths defined in PATH environment variable
        - Path can be set also in an environment variable (e.g.: $MY_PKCS_LIB)
    - `user_pin`: Pin to your HSM
        - Pin can be placed directly in the config string (not recommended!)
        - You may place your pin into environment variable (e.g: $MY_PKCS_PIN)
        - You may place your pin into a file, then simply provide the path
    - `token_label` and/or `token_serial`: Label or serial to identify the Token in your HSM containing your key
    - `key_label` and/or `key_id`: Label or ID to identify the key you want to use

* Configuration string example:
    - `type=pkcs11;so_path:c:/SoftHSM2/lib/softhsm2-x64.dll;user_pin=~/test_pin.txt;token_label=My token 1;key_label=rsa_2048`

Limitations
-----------

Currently the plugin doesn't wok on Windows when using Python 3.12 (https://github.com/pyauth/python-pkcs11/issues/165)


Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [SPSDK Signature Provider project template](https://github.com/nxp-mcuxpresso/spsdk/blob/master/examples/plugins/templates/cookiecutter-spsdk-sp-plugin.zip).
