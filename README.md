# Carbon emissions from LULC change

## Purpose

The purpose of this plugin is to calculate carbon emissions from land use and land cover (LULC) change, given an area of
interest and a specific observation period. The plugin provides a GeoTIFF of the LULC classification at the beginning
and at the end of the observation period, a GeoTIFF showing the LULC change carbon emissions in t/ha, and two CSV files
with statistics such as LULC change area by change type, emissions by change type, total net emissions, total gross
emissions, total carbon sink, and total change area. It also provides a Geopackage file with the emissions per hectare
and the absolute emissions of each LULC change.

## Installation

Use git to clone this repository to your computer.

We use mamba (i.e. conda) as an environment management system. Make sure you have it installed. Apart from python,
pytest, pydantic and pip, there is only one fixed dependency for you, which is the climatoology package that holds all
the infrastructure functionality.

Please set up the Python environment by running the following commands:

```
mamba create -f environment.yaml
mamba activate ghg-emission-from-lulc-change
```

## Usage

The plugin uses a LULC classification provided by
the [LULC utility](https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/lulc-utility). The LULC utility
processes satellite images to create two distinct land use and land cover (LULC) classifications: one representing the
beginning and another representing the end of the observation period. Since individual satellite images vary in quality
due to factors like cloud cover, the utility combines multiple images for each classification. To generate accurate
results, users need to specify a time period for which the utility will use satellite images. We recommend setting these
periods to one month, ensuring an ample supply of images for robust LULC classifications.

For optimal results, it's advisable to choose time periods falling between May and September, particularly in temperate
regions of the northern hemisphere. This timeframe increases the likelihood of obtaining cloud-free images. Please note
that this utility supports observation periods from 2017 onwards.

In ghg_lulc/test_plugin.py, please adjust the following parameters to your needs:

- area_coords: Coordinates defining the bounding box of your area of interest
- start_date_1: Start date for LULC classification at the beginning of the observation period
- end_date_1: End date for LULC classification at the beginning of the observation period
- start_date_2: Start date for LULC classification at the end of the observation period
- end_date_2: End date for LULC classification at the end of the observation period

When you have adjusted your settings, execute the plugin by running ghg_lulc/test_plugin.py using pytest.

More information on the [methodology](resources/methodology.md)

## Contribute

Contributions are welcome. Feel free to create a merge request and contact
the [CA team](mailto:climate-action@heigit.org).