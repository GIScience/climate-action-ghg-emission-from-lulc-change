import os
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
    emission_factors = calc_emission_factors(get_ghg_stock(lulc_utility_mock.get_class_legend()))
    return EmissionCalculator(emission_factors[GhgStockSource.HANSIS], computation_resources)


def test_get_change_info(default_calculator):
    """test whether LULC changes are derived correctly"""
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
            [0, 0, 0, 0, 0],
            [2, 7, 12, -1, -1],
            [3, 8, -1, 13, -1],
            [4, -1, 9, 14, -1],
            [0, 0, 0, -1, -1],
        ],
        mask=np.zeros(shape=(5, 5)),
    )
    expected_output_colormap = {
        -1: [0, 0, 0],
        0: [128, 128, 128],
        2: [107, 110, 207],
        3: [99, 121, 57],
        4: [140, 162, 82],
        7: [231, 186, 82],
        8: [231, 203, 148],
        9: [132, 60, 57],
        12: [165, 81, 148],
        13: [206, 109, 189],
        14: [222, 158, 214],
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
        -1: [0, 0, 0],
        0: [128, 128, 128],
        2: [222, 158, 214],
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
        -999.999: [0, 0, 0],
        -1.82: [0, 0, 76],
        -1.45: [0, 0, 149],
        -0.915: [0, 0, 253],
        -0.905: [1, 1, 255],
        -0.535: [105, 105, 255],
        -0.37: [149, 149, 255],
        0.0: [255, 253, 253],
        0.37: [255, 149, 149],
        0.535: [255, 105, 105],
        0.905: [255, 1, 1],
        0.915: [254, 0, 0],
        1.45: [179, 0, 0],
        1.82: [128, 0, 0],
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
        -999.999: [0, 0, 0],
        -1.82: [0, 0, 76],
        -1.45: [0, 0, 149],
        -0.915: [0, 0, 253],
        -0.905: [1, 1, 255],
        -0.535: [105, 105, 255],
        -0.37: [149, 149, 255],
        0.0: [255, 253, 253],
        0.37: [255, 149, 149],
        0.535: [255, 105, 105],
        0.905: [255, 1, 1],
        0.915: [254, 0, 0],
        1.45: [179, 0, 0],
        1.82: [128, 0, 0],
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
    """tests whether absolute emissions per polygon are calculated correctly"""
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
    """tests if the summary stats are correctly calculated"""
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

    data = [
        ['Area of interest [ha]', 0.1],
        ['Change share [%]', 20],
        ['Emitting area [ha]', 0.01],
        ['Emitting area share [%]', 50],
        ['Sink area [ha]', 0.01],
        ['Sink area share [%]', 50],
        ['Total gross emissions [t]', 1],
        ['Total sink [t]', -1],
        ['Net emissions [t]', 0],
    ]

    expected_summary = pd.DataFrame(data, columns=['Metric name', 'Value'])
    expected_summary.set_index('Metric name', inplace=True)

    calculated_summary = default_calculator.summary_stats(emissions_df, aoi)

    pd.testing.assert_frame_equal(calculated_summary, expected_summary)


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
    """tests whether the Chart2dData object is generated correctly and the areas chart file is saved"""
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

    shares = [0.5, 0.5]

    area_chart_data, areas_chart_file = default_calculator.area_plot(emissions_df)

    assert area_chart_data.x == ['built-up to forest', 'forest to built-up']
    assert area_chart_data.y == shares
    assert area_chart_data.color[0] == Color('red')
    assert os.path.exists(areas_chart_file) is True


def test_emission_plot(default_calculator):
    """tests whether the Chart2dData object is generated correctly and the emissions chart file is saved"""
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

    emission_chart_data, emission_chart_file = default_calculator.emission_plot(emissions_df)

    assert emission_chart_data.x == ['built-up to forest', 'forest to built-up']
    assert emission_chart_data.y == [-1, 1]
    assert emission_chart_data.color[0] == Color('red')
    assert os.path.exists(emission_chart_file) is True


def test_filter_ghg_stock(lulc_utility_mock):
    input = get_ghg_stock(lulc_utility_mock.get_class_legend())[GhgStockSource.HANSIS]

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
