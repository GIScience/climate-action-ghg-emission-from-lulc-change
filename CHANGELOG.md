# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project mostly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.0.1)

### Changed
- Update the Docker registry

### Fixed
- an issue caused by the ohsome-py library that prevented setting the correct logging level
- an issue induced by an update of pydantic that would break plugin representation in the front-end (see [climatoology#105](https://gitlab.heigit.org/climate-action/climatoology/-/issues/105))

### Added
- Class AOIProperties with name and ID of the AOI

## [2.0.0](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.0.0)

### Changed
- Split summary table into a summary table and an AOI info table

### Removed
- GeoJSON LULC change emission map
- Charts exported as image artifacts

### Fixed
- Color and legend of maps ([#43](https://gitlab.heigit.org/climate-action/plugins/ghg-emission-from-lulc-change/-/issues/43))
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