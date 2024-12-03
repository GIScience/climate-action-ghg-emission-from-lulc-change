import uuid

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import pytest
from affine import Affine
from climatoology.base.artifact import RasterInfo
from climatoology.base.computation import ComputationScope
from numpy import ma
from pydantic_extra_types.color import Color
from rasterio import CRS
from shapely import MultiPolygon
from shapely.geometry import Polygon
from shapely.ops import transform

from ghg_lulc.emissions import EmissionCalculator
from ghg_lulc.utils import GhgStockSource, calc_emission_factors, get_ghg_stock


@pytest.fixture()
def computation_resources():
    with ComputationScope(uuid.uuid4()) as resources:
        yield resources


@pytest.fixture()
def default_calculator(lulc_utility_mock, computation_resources):
    emission_factors = calc_emission_factors(get_ghg_stock(lulc_utility_mock.get_class_legend().osm))
    return EmissionCalculator(emission_factors[GhgStockSource.HANSIS], computation_resources)


def test_get_change_info(default_calculator):
    lulc_before = RasterInfo(
        data=ma.masked_array(
            [
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 0],
            ],
            mask=np.zeros(shape=(5, 5)),
        ),
        crs=CRS.from_epsg(4326),
        transformation=Affine.identity(),
    )
    lulc_after = RasterInfo(
        data=ma.masked_array(
            [
                [1, 2, 3, 4, 5],
                [2, 3, 4, 5, 0],
                [3, 4, 5, 1, 2],
                [4, 5, 1, 2, 3],
                [1, 2, 3, 0, 1],
            ],
            mask=np.zeros(shape=(5, 5)),
        ),
        crs=CRS.from_epsg(4326),
        transformation=Affine.identity(),
    )

    expected_output_array = ma.masked_array(
        [
            (0, 0, 0, 0, 0),
            (2, 7, 12, 255, 255),
            (3, 8, 255, 13, 255),
            (4, 255, 9, 14, 255),
            (0, 0, 0, 255, 255),
        ],
        mask=np.zeros(shape=(5, 5)),
    )
    expected_output_colormap = {
        0: (128, 128, 128),
        2: (107, 110, 207),
        3: (99, 121, 57),
        4: (140, 162, 82),
        7: (231, 186, 82),
        8: (231, 203, 148),
        9: (132, 60, 57),
        12: (165, 81, 148),
        13: (206, 109, 189),
        14: (222, 158, 214),
    }

    changes = default_calculator.get_change_info(lulc_before, lulc_after)

    assert ma.allequal(changes.data, expected_output_array)
    assert np.array_equal(changes.data.mask, expected_output_array.mask)
    assert changes.colormap == expected_output_colormap


def test_masked_change_info(default_calculator):
    lulc_before = RasterInfo(
        data=ma.masked_array([[1, 2]], mask=[0, 1]),
        crs=CRS.from_epsg(4326),
        transformation=Affine.identity(),
    )
    lulc_after = RasterInfo(
        data=ma.masked_array([[2, 3]], mask=[0, 1]),
        crs=CRS.from_epsg(4326),
        transformation=Affine.identity(),
    )

    expected_output_array = ma.masked_array(
        [[2, 7]],
        mask=[0, 1],
        dtype=np.int16,
    )
    expected_output_colormap = {
        0: (128, 128, 128),
        2: (222, 158, 214),
    }

    changes = default_calculator.get_change_info(lulc_before, lulc_after)

    assert ma.allequal(changes.data, expected_output_array)
    assert np.array_equal(changes.data.mask, expected_output_array.mask)
    assert changes.colormap == expected_output_colormap


def test_get_change_emissions_info(default_calculator):
    change = RasterInfo(
        data=ma.masked_array([[0, 2, -1]], mask=[[0, 0, 0]]),
        crs=CRS.from_epsg(4326),
        transformation=Affine.identity(),
    )

    expected_output_array = ma.masked_array(
        [[0, 0.915, -999.999]],
        mask=[[0, 0, 0]],
    )
    expected_output_colormap = {
        -1.82: (13, 8, 135),
        -1.45: (67, 3, 158),
        -0.915: (125, 3, 168),
        -0.905: (126, 3, 168),
        -0.535: (162, 29, 154),
        -0.37: (176, 41, 145),
        0.0: (204, 71, 120),
        0.37: (226, 101, 97),
        0.535: (233, 114, 87),
        0.905: (248, 148, 65),
        0.915: (248, 149, 64),
        1.45: (252, 205, 37),
        1.82: (240, 249, 33),
    }
    change_emissions = default_calculator.get_change_emissions_info(change)

    assert ma.allequal(change_emissions.data, expected_output_array)
    assert np.array_equal(change_emissions.data.mask, expected_output_array.mask)
    assert change_emissions.colormap == expected_output_colormap


def test_get_masked_change_emissions_info(default_calculator):
    change = RasterInfo(
        data=ma.masked_array([[0, 2, -1]], mask=[[0, 1, 0]]),
        crs=CRS.from_epsg(4326),
        transformation=Affine.identity(),
    )

    expected_output_array = ma.masked_array([[0, 0.915, -999.999]], mask=[[0, 1, 0]])
    expected_output_colormap = {
        -1.82: (13, 8, 135),
        -1.45: (67, 3, 158),
        -0.915: (125, 3, 168),
        -0.905: (126, 3, 168),
        -0.535: (162, 29, 154),
        -0.37: (176, 41, 145),
        0.0: (204, 71, 120),
        0.37: (226, 101, 97),
        0.535: (233, 114, 87),
        0.905: (248, 148, 65),
        0.915: (248, 149, 64),
        1.45: (252, 205, 37),
        1.82: (240, 249, 33),
    }

    change_emissions = default_calculator.get_change_emissions_info(change)

    assert ma.allequal(change_emissions.data, expected_output_array)
    assert np.array_equal(change_emissions.data.mask, expected_output_array.mask)
    assert change_emissions.colormap == expected_output_colormap


def test_convert_change_raster(default_calculator):
    changes = RasterInfo(
        data=ma.masked_array(
            [[-1, 5, 2], [7, 7, 0]],
            mask=np.zeros(
                shape=(3, 2),
            ),
            dtype=np.int16,
        ),
        crs=CRS.from_epsg(4326),
        transformation=Affine.identity(),
    )

    expected_df = {
        'change_id': [2, 5, 7],
        'utility_class_name_before': ['forest', 'grass', 'grass'],
        'raster_value_before': [1, 2, 2],
        'utility_class_name_after': ['grass', 'forest', 'farmland'],
        'raster_value_after': [2, 1, 3],
    }
    expected_df = pd.DataFrame(expected_df)

    emission_factor_df = default_calculator.convert_change_raster(changes)

    assert emission_factor_df.crs == CRS.from_epsg(32631)
    pd.testing.assert_frame_equal(
        pd.DataFrame(emission_factor_df.drop(['geometry', 'emission_factor', 'color'], axis=1)), expected_df
    )


def test_convert_masked_change_raster(default_calculator):
    changes = RasterInfo(
        data=ma.masked_array([[-1, 5, 2], [7, 7, 0]], dtype=np.int16, mask=[[0, 0, 1], [0, 1, 0]]),
        crs=CRS.from_epsg(4326),
        transformation=Affine.identity(),
    )

    expected_df = {
        'change_id': [5, 7],
        'utility_class_name_before': ['grass', 'grass'],
        'raster_value_before': [2, 2],
        'utility_class_name_after': ['forest', 'farmland'],
        'raster_value_after': [1, 3],
    }
    expected_df = pd.DataFrame(expected_df)

    emission_factor_df = default_calculator.convert_change_raster(changes)

    assert emission_factor_df.crs == CRS.from_epsg(32631)
    pd.testing.assert_frame_equal(
        pd.DataFrame(emission_factor_df.drop(['geometry', 'emission_factor', 'color'], axis=1)), expected_df
    )


def test_calculate_absolute_emissions_per_poly():
    polygons = [
        Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]),
        Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]),
        Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]),
        Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]),
    ]
    emissions_per_ha = [-1.5, 1, 10, -1.5]
    changes_df = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:32632')
    changes_df['emission_factor'] = emissions_per_ha

    expected_emissions = pd.Series(data=[-1.5, 1, 0.001, -0.00015], name='emissions')

    calculated_emissions_df = EmissionCalculator.calculate_absolute_emissions_per_poly(changes_df)

    pd.testing.assert_series_equal(calculated_emissions_df['emissions'], expected_emissions)


def test_summary_stats(default_calculator):
    proj_aoi = MultiPolygon([[((0, 0), (0, 100), (10, 100), (10, 0), (0, 0))]])
    wgs84 = pyproj.CRS('EPSG:4326')
    target_proj = pyproj.CRS('EPSG:32632')
    project = pyproj.Transformer.from_crs(target_proj, wgs84, always_xy=True).transform
    aoi = transform(project, proj_aoi)

    polygons = [
        Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]),
        Polygon([(10, 100), (10, 90), (0, 90), (0, 100), (10, 100)]),
    ]
    emissions_df = gpd.GeoDataFrame(geometry=polygons, crs=target_proj)
    emissions_df['emissions'] = [-1, 1]

    data_summary = [
        ['Gross Emissions', 1],
        ['Gross Sink', -1],
        ['Net Emissions/Sink', 0],
    ]

    data_area_info = [
        ['Area of Interest (AOI)', 0.1, 100.0],
        ['Change Area', 0.02, 20.0],
        ['Emitting Area', 0.01, 10.0],
        ['Sink Area', 0.01, 10.0],
    ]

    expected_summary = pd.DataFrame(data_summary, columns=['Metric Name', 'Value [t]'])
    expected_summary.set_index('Metric Name', inplace=True)

    expected_area_info = pd.DataFrame(
        data_area_info, columns=['Metric Name', 'Absolute Value [ha]', 'Proportion of AOI [%]']
    )
    expected_area_info.set_index('Metric Name', inplace=True)

    calculated_emission_info, calculated_area_info = default_calculator.summary_stats(emissions_df, aoi)

    pd.testing.assert_frame_equal(calculated_emission_info, expected_summary)
    pd.testing.assert_frame_equal(calculated_area_info, expected_area_info)


def test_get_change_type_table(default_calculator):
    polygons = [
        Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]),
        Polygon([(10, 100), (10, 90), (0, 90), (0, 100), (10, 100)]),
    ]
    data = {
        'emissions': [-0.01, 0.01],
        'color': [Color('red'), Color('green')],
        'utility_class_name_before': ['built-up', 'forest'],
        'utility_class_name_after': ['forest', 'built-up'],
    }
    emissions_df = gpd.GeoDataFrame(data=data, geometry=polygons, crs=pyproj.CRS('EPSG:32632'))

    data = {
        'Change': ['built-up to forest', 'forest to built-up'],
        'Area [ha]': [0.01, 0.01],
        'Total emissions [t]': [-0.01, 0.01],
    }
    expected_table = pd.DataFrame(data)
    expected_table.set_index('Change', inplace=True)

    calculated_table = default_calculator.get_change_type_table(emissions_df)

    pd.testing.assert_frame_equal(calculated_table, expected_table)


def test_area_plot(default_calculator):
    polygons = [
        Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]),
        Polygon([(10, 100), (10, 90), (0, 90), (0, 100), (10, 100)]),
    ]
    data = {
        'emissions': [-1, 1],
        'color': [Color('red'), Color('green')],
        'utility_class_name_before': ['built-up', 'forest'],
        'utility_class_name_after': ['forest', 'built-up'],
    }
    emissions_df = gpd.GeoDataFrame(data=data, geometry=polygons, crs=pyproj.CRS('EPSG:32632'))

    shares = [0.01, 0.01]

    area_chart_data = default_calculator.area_plot(emissions_df)

    assert area_chart_data.x == ['built-up to forest', 'forest to built-up']
    assert area_chart_data.y == shares
    assert area_chart_data.color[0] == Color('red')


def test_emission_plot(default_calculator):
    polygons = [
        Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]),
        Polygon([(10, 100), (10, 90), (0, 90), (0, 100), (10, 100)]),
    ]
    data = {
        'emissions': [-1, 1],
        'color': [Color('red'), Color('green')],
        'utility_class_name_before': ['built-up', 'forest'],
        'utility_class_name_after': ['forest', 'built-up'],
    }
    emissions_df = gpd.GeoDataFrame(data=data, geometry=polygons, crs=pyproj.CRS('EPSG:32632'))

    emission_chart_data = default_calculator.emission_plot(emissions_df)

    assert emission_chart_data.x == ['built-up to forest', 'forest to built-up']
    assert emission_chart_data.y == [-1, 1]
    assert emission_chart_data.color[0] == Color('grey')


def test_filter_ghg_stock(lulc_utility_mock):
    input = get_ghg_stock(lulc_utility_mock.get_class_legend().osm)[GhgStockSource.HANSIS]

    expected_output = pd.DataFrame(
        {
            'Class': ['built-up', 'farmland', 'grass', 'forest'],
            'Definition': ['Sealed surface', 'A farmland', 'A grass patch', 'A forest'],
            'GHG stock value [t/ha]': [71, 108, 161.5, 253],
        }
    )
    expected_output.set_index('Class', inplace=True)

    calculated_output = EmissionCalculator.filter_ghg_stock(input)

    pd.testing.assert_frame_equal(calculated_output, expected_output)
