import uuid

import numpy as np
import pytest
import geopandas as gpd
import os
import pandas as pd
from shapely.geometry import Polygon

from climatoology.base.operator import ComputationScope
from ghg_lulc.emissions import EmissionCalculator


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
    changes = calculator.derive_lulc_changes(lulc_array1, lulc_array2)
    assert np.array_equal(changes, np.array([[1, 2, 3, 4, 5],
                                             [-11, 0, 0, -6, 8],
                                             [0, 10, 0, 7, -9],
                                             [-7, 9, 0, -10, 0],
                                             [1, 2, 3, 4, 5]]))


def test_allocate_emissions(computation_resources):
    changes = {'change_id': [1, 2, 3, 4, 5, -11, 0, 0, -6, 8, 0, 10, 0, 7, -9, -7, 9, 0, -10, 0, 1, 2, 3, 4, 5]}
    changes = gpd.GeoDataFrame(changes)
    emission_factors = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 1.5), (7, 35), (8, 36.5), (9, 119.5),
                        (10, 121), (11, 156)]
    expected_df = {'change_id': [1, 2, 3, 4, 5, -11, 0, 0, -6, 8, 0, 10, 0, 7, -9, -7, 9, 0, -10, 0, 1, 2, 3, 4, 5],
                   'emissions_per_ha': [0, 0, 0, 0, 0, -156, 0, 0, -1.5, 36.5, 0, 121, 0, 35, -119.5, -35, 119.5, 0,
                                        -121, 0, 0, 0, 0, 0, 0]}
    expected_df = gpd.GeoDataFrame(expected_df)
    calculator = EmissionCalculator(computation_resources.computation_dir)
    emission_factor_df = calculator.allocate_emissions(changes, emission_factors)
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
    emission_factor_df['emissions_per_ha'] = emissions_per_ha
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
    emission_factor_df['emissions_per_ha'] = emissions_per_ha

    area = [1, 1, 1, 1, 1]
    expected_ef_df = emission_factor_df
    expected_ef_df['area'] = area

    d = {'emissions_per_ha': [0, 35, 119.5], 'area_change_type': [2.0, 2.0, 1.0]}
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
    emission_factor_df['emissions_per_ha'] = emissions_per_ha
    emission_factor_df['area'] = area

    emissions = [0, -7.5, 140, -109.5, 239]
    expected_ef_df = emission_factor_df
    expected_ef_df['emissions'] = emissions

    emission_factor_df = EmissionCalculator.calculate_absolute_emissions_per_poly(emission_factor_df)
    assert emission_factor_df.equals(expected_ef_df)


def test_export_vector(computation_resources):
    """tests whether vector emission map is exported properly"""
    polygons = [
        Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]),
        Polygon([(100, 0), (100, 100), (200, 100), (200, 0), (100, 0)]),
        Polygon([(200, 0), (200, 100), (300, 100), (300, 0), (200, 0)]),
        Polygon([(300, 0), (300, 100), (400, 100), (400, 0), (300, 0)]),
        Polygon([(400, 0), (400, 100), (500, 100), (500, 0), (400, 0)])
    ]
    emissions_per_ha = [0, -1.5, 35, -36.5, 119.5]
    emission_factor_df = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:25832')
    emission_factor_df['emissions_per_ha'] = emissions_per_ha
    calculator = EmissionCalculator(computation_resources.computation_dir)
    change_vector_file = calculator.export_vector(emission_factor_df)
    assert os.path.exists(change_vector_file) is True


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
    emission_factor_df['emissions_per_ha'] = emissions_per_ha
    emission_factor_df['emissions'] = emissions

    d = {'emissions_per_ha': [-36.5, 0.0, 119.5], 'emissions_change_type': [-117.0, 0.0, 379.0]}
    expected_e_df = pd.DataFrame(data=d)

    emission_sum_df = EmissionCalculator.calculate_emissions_by_change_type(emission_factor_df)
    assert emission_sum_df.equals(expected_e_df)


def test_change_type_stats(computation_resources):
    """tests whether dataframes have been merged correctly and csv file has been exported"""
    d = {'emissions_per_ha': [0.0, 35.0, 119.5], 'area_change_type': [2.0, 2.0, 1.0]}
    area_df = pd.DataFrame(data=d)

    d = {'emissions_per_ha': [35.0, 0.0, 119.5], 'emissions_change_type': [117.0, 0.0, 379.0]}
    emission_sum_df = pd.DataFrame(data=d)

    d = {'emissions_per_ha': [0.0, 35.0, 119.5], 'area_change_type': [2.0, 2.0, 1.0],
         'emissions_change_type': [0.0, 117.0, 379.0], 'change_type': ['no LULC change', 'farmland to settlement',
                                                                       'forest to meadow']}
    expected_out_df = pd.DataFrame(data=d)

    emissions_calculator = EmissionCalculator(compute_dir=computation_resources.computation_dir)
    out_df, change_type_file = emissions_calculator.change_type_stats(area_df, emission_sum_df)
    assert out_df.equals(expected_out_df)
    assert os.path.exists(change_type_file) is True


def test_summary_stats(computation_resources):
    """tests whether the csv file with the summary statistics has been exported"""
    total_area = 348.0
    total_net_emissions = 48.0
    total_gross_emissions = 1984.0
    total_sink = -1936.0

    calculator = EmissionCalculator(compute_dir=computation_resources.computation_dir)
    summary_file = calculator.summary_stats(total_area, total_net_emissions, total_gross_emissions, total_sink)
    assert os.path.exists(summary_file) is True


def test_area_plot(computation_resources):
    """tests whether the areas chart file is saved"""
    d = {'emissions_per_ha': [0.0, 35.0, 119.5], 'area_change_type': [2.0, 2.0, 1.0],
         'emissions_change_type': [0.0, 117.0, 379.0], 'change_type': ['no LULC change', 'farmland to settlement',
                                                                       'forest to meadow']}
    out_df = pd.DataFrame(data=d)
    calculator = EmissionCalculator(compute_dir=computation_resources.computation_dir)
    areas_chart_file = calculator.area_plot(out_df)
    assert os.path.exists(areas_chart_file) is True


def test_emission_plot(computation_resources):
    """tests whether the emissions chart file is saved"""
    d = {'emissions_change_type': [-23, -35, -25, -67, -10, -64, 12, 24, 35, 49, 67, 25],
         'change_type': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l']}
    out_df = pd.DataFrame(data=d)
    calculator = EmissionCalculator(compute_dir=computation_resources.computation_dir)
    emission_chart_file = calculator.emission_plot(out_df)
    assert os.path.exists(emission_chart_file) is True
