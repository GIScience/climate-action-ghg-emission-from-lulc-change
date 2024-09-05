# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project mostly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/plugins/ghg-emission-from-lulc-change/-/compare/2.0.0...main?from_project_id=765&straight=false)

### Changed
- Update the Docker registry

### Added
- Class AOIProperties with name and ID of the AOI

## [2.0.0](https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/2.0.0)

### Changed
- Split summary table into a summary table and an AOI info table

### Removed
- GeoJSON LULC change emission map
- Charts exported as image artifacts

### Fixed
- Color and legend of maps
- Fix and update descriptions

### Added
- License

## [1.0.0](https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/plugins/ghg-emission-from-lulc-change/-/releases/1.0.0)

### Added
- First version of calculation of GHG emissions from LULC change
- Raster artifacts: LULC classifications before and after, LULC changes, LULC change emissions
- GeoJSON artifacts: LULC change emissions
- Image artifacts: LULC change areas pie chart, LULC change emissions horizontal bar chart
- Chart artifacts: LULC change areas pie chart, LULC change emissions bar chart
- Table artifacts: Summary table, Carbon stocks, Change areas and emissions by LULC change type
- Markdown artifacts: Artifact description