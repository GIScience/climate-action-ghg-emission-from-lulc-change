
# <img src="resources/icon.jpeg" width="5%"> Carbon emissions from LULC change

The purpose of this plugin is to estimate carbon emissions from land use and land cover (LULC) change, given a selected area of interest and observation period.
The plugin provides maps of the LULC classification at the beginning and at the end of the observation period, as well as maps of the LULC changes.
Additionally, tables and plots with information on the LULC change areas and LULC change emissions are produced.
For more documentation see the [climate action website](https://climate-action.heigit.org/) or the [purpose](resources/purpose.md), [methodology](resources/methodology.md) and [sources](resources/sources.bib) files in the [resources directory](resources).

## Preparation

Use git to clone this repository to your computer.

Create a new branch by running `git checkout -b <my_new_branch_name>`.
After you have finished your implementation, you can create a merge request to the main branch that can be reviewed by the CA team.
We highly encourage you to create smaller intermediate MRs for review!

### Python Environment

We use [poetry](https://python-poetry.org/) as an environment management system.
Make sure you have it installed.
Apart from some base dependencies, there is only one fixed dependency for you, which is the [climatoology](https://gitlab.heigit.org/climate-action/climatoology) package that holds all the infrastructure functionality.
Make sure you have read-access to the climatoology repository (i.e. you can clone it).

Now run
```
poetry install --no-root
```
and you are ready to code within your poetry environment.

### Testing

We use [pytest](pytest.org) as testing engine.
Write tests to test your code and ensure all tests are passing by running poetry run pytest.

### Linting and formatting

It is important that the code created by the different plugin developers adheres to a certain standard.
We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting the code as part of our pre-commit hooks.
Please activate pre-commit by running `poetry run pre-commit install`.
It will now run automatically before each commit and apply fixes for a variety of lint errors to your code.
Note that we have increased the maximum number of characters per line to be 120 to make better use of large modern displays.
If you want to keep short lines explicitly seperate (e.g. in the definition of functions or list) please use ["magic trailing commas"](https://docs.astral.sh/ruff/settings/#format_skip-magic-trailing-comma).

### Logging

Using the environment variable `LOG_Level` you can adjust the amount of log messages produced by the plugin.
Please make sure to use logging throughout your plugin.
This will make debugging easier at a later stage.

## Functionality

We have seperated the code into multiple files by their functionality.
We will go through these files step by step.

### Tests

#### Tests in [test_plugin.py](test/test_plugin.py)

[Test driven development](https://en.wikipedia.org/wiki/Test-driven_development) is highly encouraged.

 - The first test confirms that the plugin announcement is working as expected (`test_plugin_info_request`).
 - The second test ensures that the computation runs as expected in a test environment (`test_plugin_compute_request`).

These tests ensure that the development contract is met.

#### Tests in [conftest.py](test/conftest.py)

This file contains fixtures where the expected compute input is given (`expected_compute_input`) and the LULC utility (`lulc_utility_mock`) is mocked.

#### Other tests

The files [test_emissions.py](test/test_emissions.py) and [test_utils.py](test/test_utils.py) contain tests of the functions in the files [emissions.py](ghg_lulc/emissions.py) and [utils.py](ghg_lulc/utils.py).

### Operator in [operator_worker.py](ghg_lulc/operator_worker.py)

This is the heart of the plugin where the emission estimation happens.
The most important functions are the info function and the compute function.
The info function simply returns information about the plugin.
The compute function estimates the emissions and returns the outputs of the operator as a list of artifacts.

### Input parameters in [input.py](plugin_blueprint/input.py)

The input parameters are defined here and some validation on them is done.

### Other Python files in [ghg_lulc](ghg_lulc)

- The file [emissions.py](ghg_lulc/emissions.py) contains the functions of the emission calculator.
- The file [utils.py](ghg_lulc/utils.py) contains mischellaneous functions.
- The file [artifact.py](ghg_lulc/artifact.py) contains the functions that create the artifacts.

## Contribute

Contributions are welcome. Feel free to create a merge request and contact
the [CA team](mailto:climate-action@heigit.org).

You can find more information about the methodology of the plugin in the [documentation](resources/docs/documentation.md).