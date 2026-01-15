# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project mostly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/compare/2.3.3...main)
- Refactor plugin and reorganize project structure ([#108](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/108))

### Changed
- Add teaser to plugin and restore the previous purpose
- Update the plugin to use the climatoology version 7.0.0
- Change the color map for the lulc change map ([#96](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/96))

- Assigning new artifact tags instead of the default version (primary/non-primary) ([#106](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/106))

## [2.3.3](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.3.3) - 2025-06-13

### Fixed

- update climatoology to include the LULC Utility fix, which refines the binning of the AOI to avoid out of memory
  issues ([LULC Utility #83](https://gitlab.heigit.org/climate-action/utilities/lulc-utility/-/issues/83))

## [2.3.2](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.3.2) - 2025-06-04

- Update climatoology to 6.4.2

## [2.3.0](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.3.0)

### Changed

- Ensure that plugin content meets content guidelines, ensure consistent terminology throughout plugin: Edit purpose, methodology, artifact captions and descriptions, rename input parameters ([#99](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/99))
- Remove duplications between artifact captions and artifact descriptions ([#101](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/101))
- Docker builds now take the commit hash as an argument to avoid version collisions on staging ([#103](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/103))
- CI pipeline now includes test-coverage checks ([#102](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/102))

### Removed

- Artifact description artifact, as the descriptions now appear under each respective artifact ([#99](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/99))

## [2.2.0](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.2.0)

### Changed

- Allow only selection of years for `Period start` and `Period end` inputs ([#97](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/97))
- Make LULC utility use images from a one-month period instead of just one week for higher stability ([#97](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/97)
- Rename plugin to `LULC Change`
- Update climatoology to 6.4.1
- CI pipeline now includes test-coverage checks ([#102](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/102))
- Updated ruff and pre-commit configs for more checks ([#92](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/92))

### Removed

- Input parameter `accuracy threshold` - It is set to 0.75 ([#97](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/97))

### Added

- Validation checks ensure the selected AOI stays within size limits (1000 sqkm) and overlaps with Germany's borders ([94](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/94) and [83](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/83))

## [2.1.0](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.1.0)

### Changed

- modified plugin code for compatibility with `climatoology [version 6.0.2]`, now `climatoology` utilizes the Celery
  library as the core task manager. This also means that a postgres server, that serves as the result backend for
  Celery, is now required to run the plugin.
- account for new explicit AOI input by moving it from the input parameters of `ComputeInput`class
- changed results color scheme to `coolwarm` for compatibility with climatoology's accepted color schemes
- Update climatoology to 6.3.1: include `demo_input_parameters` in info

## [2.0.1](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.0.1)

### Changed

- Update the Docker registry

### Fixed

- an issue caused by the ohsome-py library that prevented setting the correct logging level
- an issue induced by an update of pydantic that would break plugin representation in the front-end (
  see [climatoology#105](https://gitlab.heigit.org/climate-action/climatoology/-/issues/105))

### Added

- Class AOIProperties with name and ID of the AOI

## [2.0.0](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.0.0)

### Changed

- Split summary table into a summary table and an AOI info table

### Removed

- GeoJSON LULC change emission map
- Charts exported as image artifacts

### Fixed

- Color and legend of
  maps ([#43](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/43))
- Fix and update descriptions

### Added

- License

## [1.0.0](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/1.0.0)

### Added

- First version of calculation of GHG emissions from LULC change
- Raster artifacts: LULC classifications before and after, LULC changes, LULC change emissions
- GeoJSON artifacts: LULC change emissions
- Image artifacts: LULC change areas pie chart, LULC change emissions horizontal bar chart
- Chart artifacts: LULC change areas pie chart, LULC change emissions bar chart
- Table artifacts: Summary table, Carbon stocks, Change areas and emissions by LULC change type
- Markdown artifacts: Artifact description