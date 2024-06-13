NXP Python Code Checking tool
=============================


License
-------

* Free software: BSD-3-Clause


Features
--------

* Simple set of checking tools for accepting code quality for NXP python projects.
* Supported checkers:
	- Pytest - generate coverity reports
	- GitCov - Check the Pytest generated coverity reports on changed files
	- Pylint
	- MyPy
	- Radon D
	- Radon C
	- PyDocStyle
	- Dependency packages license check
	- Black (Supports fix feature)
	- iSort (Supports fix feature)
	- Copyright  (Supports fix feature)
	- Python script file header (Supports fix feature)
	- Cyclic import checker
* Supported Jupyter notebooks checkers:
	- Black (Supports fix feature)
	- iSort (Supports fix feature) 
	- Jupyter notebooks outputs check 

Installation
------------

* `pip install nxp_codecheck`
* Verify installation by running `codecheck --help`
    - you should see help for the codecheck tool

* configuration
	- Codecheck is using configuration in pyproject.toml file for custom checkers and main tool itself. The standard checker is using own settings from project
	- For custom configuration please check the pyproject.toml file of nxp_codecheck project for inspiration to Copy-Modify-Use in your enviroment


Credits
-------

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter).