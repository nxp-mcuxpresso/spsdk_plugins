
Keyfactor Signature Provider
============================

SPSDK Signature Provider plugin using Keyfactor's API


Features
--------

* Allows SPSDK to use Keyfactor for signing any arbitrary data
* Users might be authenticated using Client Certificates


Installation
------------

* Activate virtual env, where you have SPSDK
    - to install spsdk run: `pip install spsdk`
* `pip install spsdk_keyfactor`


Usage
-----

All of plugin configuration can be done via environment variables:

- `KEYFACTOR_HOST`: URL of the Keyfactor host (example: "https://ray-signserver.keyfactoriot.com")
- `KEYFACTOR_HOST_VERIFY`: Path to a TLS certificate to verify the HOST (example: "ejbcav8demo.keyfactoriot.com.pem")
- `KEYFACTOR_AUTH_TYPE`: Type of authentication in Keyfactor
    - `client_certificate_key` using client x509 certificate and private key
    - `client_certificate_pkcs12` using client PKCS#12 certificate and password (password might be stored in a file, and then password is a path to a file with the password to PKCS#12 certificate)
- `KEYFACTOR_AUTH_VALUE`: Coma-separated string of values described by `KEYFACTOR_AUTH_TYPE` (example for PKCS#12: "path_to_pkcs.p12,path_to_pass.txt")
- `KEYFACTOR_WORKER`: Name or ID of the Keyfactor Worker to use (example: "PlainSigner")
- `KEYFACTOR_PREHASH`: Client-side pre-hashing of data  (example: "SHA-256", "SHA-384")
- `KEYFACTOR_SIGNATURE_LENGTH`: Length in bytes of the raw signature (without potential DER encoding) (example: 256 for RSA, 64 for ECC-256)
    - if this setting is skipped, the plugin will autodetect the value

Environment variables may be specified in a file.
By default the plugin searches for file named `.keyfactor.env` in the following locations: `CWD`, `HOME`, `~/.config`  
The path to env file also be set via environment variable `KEYFACTOR_DOTENV_PATH`

Plugin comes with an companion app (`nxp-keyfactor`) which you may use to create a configuration file template.  
To generate a configuration file, run: `nxp-keyfactor get-template`

Once the plugin is configured, you may use it everywhere in SPSDK config files where a path to a private key or signature provider is mentioned. The identifier for this plugin is `keyfactor`.  

Example: `signProvider: type=keyfactor[;worker=myWorker]` 
- (setting the worker name/id in SPSDK config file overrides the KEYFACTOR_WORKER setting)

When you need to download a public key corresponding to your Keyfactor worker (e.g.: SRK_TABLE for AHAB) you can use the companion app.  
Example: `nxp-keyfactor get-puk --worker PlainSigner --output my_public_key.pem`

Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [SPSDK Signature Provider project template](https://github.com/nxp-mcuxpresso/spsdk/blob/master/examples/plugins/templates/cookiecutter-spsdk-sp-plugin.zip).
