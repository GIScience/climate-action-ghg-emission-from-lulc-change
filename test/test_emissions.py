import uuid

import numpy as np
import pytest
import geopandas as gpd
import os
import pandas as pd
from climatoology.base.computation import ComputationScope
from pydantic_extra_types.color import Color
from shapely.geometry import Polygon
from ghg_lulc.emissions import EmissionCalculator
from ghg_lulc.plugin import EMISSION_FACTORS, PLOT_COLORS


@pytest.fixture()
def computation_resources():
    with ComputationScope(uuid.uuid4()) as resources:
        yield resources


def test_derive_lulc_changes(computation_resources):
    """test whether LULC changes are derived correctly"""
    lulc_array1 = np.array([[1, 2, 3, 4, 5],
                            [1, 2, 3, 4, 5],
                            [1, 2, 3, 4, 5],
                            [1, 2, 3, 4, 5],
                            [1, 2, 3, 4, 5]])

    lulc_array2 = np.array([[1, 2, 3, 4, 5],
                            [2, 3, 4, 5, 1],
                            [3, 4, 5, 1, 2],
                            [4, 5, 1, 2, 3],
                            [1, 2, 3, 4, 5]])

    calculator = EmissionCalculator(computation_resources.computation_dir)
    changes, change_colormap = calculator.derive_lulc_changes(lulc_array1, lulc_array2)
    assert np.array_equal(changes, np.array([[1, 2, 3, 4, 5],
                                             [12, 0, 0, 17, 8],
                                             [0, 10, 0, 7, 14],
                                             [16, 9, 0, 13, 0],
                                             [1, 2, 3, 4, 5]]))


def test_allocate_emissions(computation_resources):
    changes = {'change_id': [1, 2, 3, 4, 5, 11, 0, 0, 12, 8, 0, 10, 0, 7, 13, 14, 9, 0, 15, 0, 1, 2, 3, 4, 5]}
    changes = gpd.GeoDataFrame(changes)

    expected_df = {'change_id': [1, 2, 3, 4, 5, 11, 0, 0, 12, 8, 0, 10, 0, 7, 13, 14, 9, 0, 15, 0, 1, 2, 3, 4, 5],
                   'emissions per ha': [0, 0, 0, 0, 0, 156, 0, 0, -156, 36.5, 0, 121, 0, 35, -121, -119.5, 119.5, 0,
                                        -36.5, 0, 0, 0, 0, 0, 0]}
    expected_df = gpd.GeoDataFrame(expected_df)
    calculator = EmissionCalculator(computation_resources.computation_dir)
    emission_factor_df = calculator.allocate_emissions(changes, EMISSION_FACTORS)
    assert emission_factor_df.equals(expected_df)


def test_calculate_total_change_area():
    """tests whether total change area is calculated correctly"""
    polygons = [
        Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]),
        Polygon([(100, 0), (100, 100), (200, 100), (200, 0), (100, 0)]),
        Polygon([(200, 0), (200, 100), (300, 100), (300, 0), (200, 0)]),
        Polygon([(300, 0), (300, 100), (400, 100), (400, 0), (300, 0)]),
        Polygon([(400, 0), (400, 100), (500, 100), (500, 0), (400, 0)])
    ]
    emissions_per_ha = [0, -1.5, 35, -36.5, 119.5]
    emission_factor_df = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:25832')
    emission_factor_df['emissions per ha'] = emissions_per_ha
    expected_area = 4
    actual_area = EmissionCalculator.calculate_total_change_area(emission_factor_df)
    assert actual_area == expected_area


def test_calculate_area_by_change_type():
    """tests whether area of LULC change types is calculated correctly"""
    polygons = [
        Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]),
        Polygon([(100, 0), (100, 100), (200, 100), (200, 0), (100, 0)]),
        Polygon([(200, 0), (200, 100), (300, 100), (300, 0), (200, 0)]),
        Polygon([(300, 0), (300, 100), (400, 100), (400, 0), (300, 0)]),
        Polygon([(400, 0), (400, 100), (500, 100), (500, 0), (400, 0)])
    ]
    emissions_per_ha = [0, 0, 35, 35, 119.5]
    emission_factor_df = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:25832')
    emission_factor_df['emissions per ha'] = emissions_per_ha

    area = [1, 1, 1, 1, 1]
    expected_ef_df = emission_factor_df
    expected_ef_df['area'] = area

    d = {'emissions per ha': [0, 35, 119.5], 'LULC change type area': [2.0, 2.0, 1.0]}
    expected_a_df = pd.DataFrame(data=d)

    emission_factor_df, area_df = EmissionCalculator.calculate_area_by_change_type(emission_factor_df)
    assert emission_factor_df.equals(expected_ef_df)
    assert area_df.equals(expected_a_df)


def test_calculate_absolute_emissions_per_poly():
    """tests whether absolute emissions per polygon are calculated correctly"""
    polygons = [
        Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]),
        Polygon([(100, 0), (100, 100), (200, 100), (200, 0), (100, 0)]),
        Polygon([(200, 0), (200, 100), (300, 100), (300, 0), (200, 0)]),
        Polygon([(300, 0), (300, 100), (400, 100), (400, 0), (300, 0)]),
        Polygon([(400, 0), (400, 100), (500, 100), (500, 0), (400, 0)])
    ]
    emissions_per_ha = [0, -1.5, 35, -36.5, 119.5]
    area = [1, 5, 4, 3, 2]
    emission_factor_df = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:25832')
    emission_factor_df['emissions per ha'] = emissions_per_ha
    emission_factor_df['area'] = area

    emissions = [0, -7.5, 140, -109.5, 239]
    expected_ef_df = emission_factor_df
    expected_ef_df['emissions'] = emissions

    emission_factor_df = EmissionCalculator.calculate_absolute_emissions_per_poly(emission_factor_df)
    assert emission_factor_df.equals(expected_ef_df)


def test_add_colormap():
    """tests whether the colors for the emission map are assigned to the LULC change objects correctly"""
    emissions = pd.Series([-376.6, -19.12, 0, 16.8, 310.97])
    colors = pd.Series([Color('#00004c'), Color('#e5e5ff'), Color('#fffdfd'), Color('#ffe9e9'), Color('#ac0000')])
    color_col = EmissionCalculator.add_colormap(emissions)
    pd.testing.assert_series_equal(color_col, colors)


def test_calculate_total_emissions():
    """tests whether total net emissions, gross emissions, and sink are calculated correctly"""
    polygons = [
        Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]),
        Polygon([(100, 0), (100, 100), (200, 100), (200, 0), (100, 0)]),
        Polygon([(200, 0), (200, 100), (300, 100), (300, 0), (200, 0)]),
        Polygon([(300, 0), (300, 100), (400, 100), (400, 0), (300, 0)]),
        Polygon([(400, 0), (400, 100), (500, 100), (500, 0), (400, 0)])
    ]
    emissions = [0, -7.5, 140, -109.5, 239]
    emission_factor_df = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:25832')
    emission_factor_df['emissions'] = emissions
    expected_net_emissions = 262
    expected_gross_emissions = 379
    expected_sink = -117
    total_net_emissions, total_gross_emissions, total_sink = EmissionCalculator.calculate_total_emissions(
        emission_factor_df)
    assert total_net_emissions == expected_net_emissions
    assert total_gross_emissions == expected_gross_emissions
    assert total_sink == expected_sink


def test_calculate_emissions_by_change_type():
    """tests whether the total emissions by change type are calculated correctly"""
    polygons = [
        Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]),
        Polygon([(100, 0), (100, 100), (200, 100), (200, 0), (100, 0)]),
        Polygon([(200, 0), (200, 100), (300, 100), (300, 0), (200, 0)]),
        Polygon([(300, 0), (300, 100), (400, 100), (400, 0), (300, 0)]),
        Polygon([(400, 0), (400, 100), (500, 100), (500, 0), (400, 0)])
    ]
    emissions_per_ha = [0, -36.5, 119.5, -36.5, 119.5]
    emissions = [0, -7.5, 140, -109.5, 239]
    emission_factor_df = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:25832')
    emission_factor_df['emissions per ha'] = emissions_per_ha
    emission_factor_df['emissions'] = emissions

    d = {'emissions per ha': [-36.5, 0.0, 119.5], 'LULC change type emissions': [-117.0, 0.0, 379.0]}
    expected_e_df = pd.DataFrame(data=d)

    emission_sum_df = EmissionCalculator.calculate_emissions_by_change_type(emission_factor_df)
    assert emission_sum_df.equals(expected_e_df)


def test_change_type_stats(computation_resources):
    """tests whether dataframes have been merged correctly and csv file has been exported"""
    d = {'emissions per ha': [0.0, 35.0, 119.5], 'LULC change type area': [2.0, 2.0, 1.0]}
    area_df = pd.DataFrame(data=d)

    d = {'emissions per ha': [35.0, 0.0, 119.5], 'LULC change type emissions': [117.0, 0.0, 379.0]}
    emission_sum_df = pd.DataFrame(data=d)

    d = {'emissions per ha': [0.0, 35.0, 119.5], 'LULC change type area': [2.0, 2.0, 1.0],
         'LULC change type emissions': [0.0, 117.0, 379.0], 'LULC change type': ['no LULC change',
                                                                                 'farmland to settlement',
                                                                                 'forest to meadow']}
    expected_out_df = pd.DataFrame(data=d)

    emissions_calculator = EmissionCalculator(compute_dir=computation_resources.computation_dir)
    out_df = emissions_calculator.change_type_stats(area_df, emission_sum_df)
    assert out_df.equals(expected_out_df)


def test_summary_stats(computation_resources):
    """tests whether the csv file with the summary statistics has been exported"""
    total_area = 348.0
    total_net_emissions = 48.0
    total_gross_emissions = 1984.0
    total_sink = -1936.0

    data = {'metric name': ['total change area [ha]', 'total net emissions [t]', 'total gross emissions [t]',
                            'total sink [t]'],
            'value': [348.0, 48.0, 1984.0, -1936.0]}
    expected_summary = pd.DataFrame(data)
    expected_summary.set_index('metric name', inplace=True)

    calculator = EmissionCalculator(compute_dir=computation_resources.computation_dir)
    summary = calculator.summary_stats(total_area, total_net_emissions, total_gross_emissions, total_sink)
    assert summary.equals(expected_summary)


def test_area_plot(computation_resources):
    """tests whether the Chart2dData object is generated correctly and the areas chart file is saved"""
    d = {'LULC change type area': [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 0, 0],
         'LULC change type': ['settlement to forest', 'farmland to forest', 'meadow to forest', 'settlement to meadow',
                              'settlement to farmland', 'farmland to meadow', 'meadow to farmland',
                              'farmland to settlement', 'meadow to settlement', 'forest to meadow',
                              'forest to farmland', 'forest to settlement']}
    out_df = pd.DataFrame(data=d)
    shares = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.0, 0.0]
    calculator = EmissionCalculator(compute_dir=computation_resources.computation_dir)
    area_chart_data, areas_chart_file = calculator.area_plot(out_df, PLOT_COLORS)
    assert area_chart_data.x == d['LULC change type']
    assert area_chart_data.y == shares
    assert area_chart_data.color[0] == Color('midnightblue')
    assert os.path.exists(areas_chart_file) is True


def test_emission_plot(computation_resources):
    """tests whether the Chart2dData object is generated correctly and the emissions chart file is saved"""
    d = {'LULC change type emissions': [-23, -35, -25, -67, -10, -64, 12, 24, 35, 49, 67, 25],
         'LULC change type': ['settlement to forest', 'farmland to forest', 'meadow to forest', 'settlement to meadow',
                              'settlement to farmland', 'farmland to meadow', 'meadow to farmland',
                              'farmland to settlement', 'meadow to settlement', 'forest to meadow',
                              'forest to farmland', 'forest to settlement']}
    out_df = pd.DataFrame(data=d)
    calculator = EmissionCalculator(compute_dir=computation_resources.computation_dir)
    emission_chart_data, emission_chart_file = calculator.emission_plot(out_df, PLOT_COLORS)
    assert emission_chart_data.x == d['LULC change type']
    assert emission_chart_data.y == d['LULC change type emissions']
    assert emission_chart_data.color[0] == Color('midnightblue')
    assert os.path.exists(emission_chart_file) is True
