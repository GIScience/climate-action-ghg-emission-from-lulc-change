
# <img src="resources/icon.jpeg" width="5%"> Carbon flows from LULC change

[![status: hibernate](https://github.com/GIScience/badges/raw/master/status/hibernate.svg)](https://github.com/GIScience/badges#hibernate)

> ⚠️ This plugin is in hibernation state. It is available as a showcase, but not actively developed. If you are interested in a collaboration on this topic, please contact us at [climate-action@heigit.org](mailto:climate-action@heigit.org).

The purpose of this plugin is to estimate carbon flows from land use and land cover (LULC) change, given a selected area of interest and analysis period.
The plugin provides maps of the LULC classification at the beginning and at the end of the analysis period, as well as maps of the LULC changes.
Additionally, tables and plots with information on the LULC change areas and carbon flows from LULC change are produced.
For more documentation see the [climate action website](https://climate-action.heigit.org/) or the [purpose](resources/purpose.md), [methodology](resources/methodology.md) and [sources](resources/sources.bib) files in the [resources directory](resources).

## Preparation

Use git to clone this repository to your computer.

Create a new branch by running `git checkout -b <my_new_branch_name>`.
After you have finished your implementation, you can create a merge request to the main branch that can be reviewed by the CA team.
We highly encourage you to create smaller intermediate MRs for review!

## Development setup

To run your plugin locally requires the following setup:

1. Set up the [infrastructure](https://gitlab.heigit.org/climate-action/infrastructure) locally in `devel` mode
2. Copy your [.env.base_template](.env.base_template) to `.env.base` and [.env_template](.env_template) to `.env` and
   update them
3. Run `poetry run python ghg_lulc/plugin.py`

### Testing

We use [pytest](https://pytest.org) as a testing engine.
Ensure all tests are passing by running `poetry run pytest`.

#### Coverage

To get a coverage report of how much of your code is run during testing, execute
`poetry run pytest --ignore test/core/ --cov`.
We ignore the `test/core/` folder when assessing coverage because the core tests run the whole plugin to be sure
everything successfully runs with a very basic configuration.
Yet, they don't actually test functionality and therefore artificially inflate the test coverage results.

To get a more detailed report including which lines in each file are **not** tested,
run `poetry run pytest --ignore test/core/ --cov --cov-report term-missing`

### Linting and formatting

It is important that the code created by the different plugin developers adheres to a certain standard.
We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting the code as part of our pre-commit hooks.
Please activate pre-commit by running `poetry run pre-commit install`.
It will now run automatically before each commit and apply fixes for a variety of lint errors to your code.

To manually run the linter and formatter, you can execute `poetry run pre-commit run -a`.

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

The files [test_emissions.py](test/test_emissions.py) and [test_utils.py](test/test_utils.py) contain tests of the functions in the files [emissions.py](ghg_lulc/components/emissions.py) and [utils.py](ghg_lulc/components/utils.py).

### Operator in [operator_worker.py](ghg_lulc/core/operator_worker.py)

This is the heart of the plugin where the emission estimation happens.
The most important functions are the info function and the compute function.
The info function simply returns information about the plugin.
The compute function estimates the carbon flows and returns the outputs of the operator as a list of artifacts.

### Input parameters in [input.py](plugin_blueprint/input.py)

The input parameters are defined here and some validation on them is done.

### Other Python files in [ghg_lulc](ghg_lulc)

- The file [emissions.py](ghg_lulc/components/emissions.py) contains the functions of the emission calculator.
- The file [utils.py](ghg_lulc/components/utils.py) contains mischellaneous functions.
- The file [artifact.py](ghg_lulc/components/raster_artifacts.py) contains the functions that create the artifacts.

## Releasing a new plugin version

To release a new plugin version

1. Update the [CHANGELOG.md](CHANGELOG.md).
   It should already be up to date but give it one last read and update the heading above this upcoming release
2. Decide on the new version number.
   We suggest you adhere to the [Semantic Versioning](https://semver.org/) scheme, based on the changes since the last
   release.
   You can think of your plugin methods (info method, input parameters and artifacts) as the public API of your plugin.
3. Update the version attribute in the [pyproject.toml](pyproject.toml) (e.g. by running
   `poetry version {patch|minor|major}`)
4. Create a [release]((https://docs.gitlab.com/ee/user/project/releases/#create-a-release-in-the-releases-page)) on
   GitLab, including a changelog

## Docker


### Build

The tool is also [Dockerised](Dockerfile).
Images are automatically built and deployed in the [CI-pipeline](.gitlab-ci.yml).

In case you want to manually build and run locally (e.g. to test a new feature in development), execute

```shell
docker build . --tag repo.heigit.org/climate-action/ghg-emission-from-lulc-change:devel
```

Note that this will overwrite any existing image with the same tag (i.e. the one you previously pulled from the Climate
Action docker registry).

To mimic the build behaviour of the CI you have to add `--build-arg CI_COMMIT_SHORT_SHA=$(git rev-parse --short HEAD)`
to the above command.

#### Canary

To build a canary version update your `climatoology` dependency declaration to point to the `main` branch and update
your lock file (`poetry update climatoology`).
Then run

```shell
docker build . \
  --build-arg CI_COMMIT_SHORT_SHA=$(git rev-parse --short HEAD) \
  --tag repo.heigit.org/climate-action/ghg-emission-from-lulc-change:canary \
  --push
```

### Run

If you have the Climate Infrastructure running (see [Development Setup](#development-setup)) you can now run the
container via

```shell
docker run --rm --network=host --env-file .env.base --env-file .env repo.heigit.org/climate-action/ghg-emission-from-lulc-change:devel
```

### Deploy

Deployment is handled by the GitLab CI automatically.
If for any reason you want to deploy manually (and have the required rights), after building the image, run

```shell
docker image push repo.heigit.org/climate-action/ghg-emission-from-lulc-change:devel
```

## Contribute

Contributions are welcome. Feel free to create a merge request and contact
the [CA team](mailto:climate-action@heigit.org).

You can find more information about the methodology of the plugin in the [documentation](resources/docs/documentation.md).