
# EdgeLock 2 GO service providers for SPSDK

Package contains multiple SPSDK service providers powered by EL2GO

* Free software: BSD-3-Clause
* Documentation: https://spsdk-el2go.readthedocs.io.


Installation
------------

* Activate virtual env, where you have SPSDK
    - if SPSDK is not installed, the latest one will be installed automatically from [PyPI](https://pypi.org/project/spsdk/)
* `pip install spsdk-el2go`


## Signature Provider

Everywhere in SPSDK where a signature (private key) is required, a signature provider can be used instead.  
Using this plugin, all signing operations can be delegated to EL2GO. Private keys stay securely stored in EL2GO servers.


### Configuration:

SPSDK Service providers are configured via a Service configuration string.
Format: `type=<service_id>[;param1=value1][;param2=value2]`  
In this case the service identifier is `el2go` thus the config string starts with `type=el2go`

EL2GO signature provider uses the following configuration options:
  * `url`: Base EL2GO API URL (default: https://api.edgelock2go.com)
  * `api_key`: EL2GO API key. Can be placed in env variable (staring with $) or a file.
    * E.g.: `~/.config/el2go/token.txt`, `$EL2GO_TOKEN`, `$PATH_TO_FILE_WITH_API_KEY`
    * make sure your API token has Code Signing permissions set (both View and Manage are required)
  * `key_set_id` (number): ID of the Key Set in EL2GO server
  * `key_id` (number): ID of the key used for signing operation
  * `config_path`: path to a YAML file containing some or all the config options above

These configuration options can be specified in service configuration string

    type=el2go;url=https://api.edgelock2go.com;api_key=~/.config/el2go/token.txt;key_set_id=4;key_id=1

or can be passed via a config file

    type=el2go;config_path=el2go_config.yaml

or a combination of both, overriding/adding options from config file in config string:

    type=el2go;config_path=el2go_config.yaml;key_id=2

To help with setting up the config file, you may use `el2go-helper` application which is bundled with this python package.  
Run `el2go-helper --help` to see more info.

### Usage


* Use the configuration string in any SPSDK YAML config file, where a private key is normally provided
  * e.g.: in MBI config file: `signer: type=el2go;config_path=el2go_config.yaml`

* Use SPSDK application as you would normally do
  * e.g.: `nxpimage mbi export -c mbi_config.yaml`


## SB Key derivation provider

Derive encryption key used for SB3 and SB4 files from key stored in EdgeLock 2 GO server


### Configuration

Exactly the same as for Signature Provider


### Usage

* Use the configuration string in SB3 or SB4 YAML config file, where the CUST_MK_SK/SBKEK is provided
  * e.g.: `containerKeyBlobEncryptionKey: type=el2go;config_path=el2go_config.yaml;key_id=20`

* Use SPSDK's nxpimage application as you would normally do
  * e.g.: `nxpimage sb31 export -c sb_config.yaml`

## Public key provider

Allow to specify any public key in YAML config file as a reference to public key stored in EdgeLock 2 GO

**Coming soon**

