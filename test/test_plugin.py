import geopandas
from geopandas.testing import assert_geodataframe_equal
from numpy.testing import assert_array_equal

from test.conftest import TEST_RESOURCES_DIR

import json
import numpy as np
import pandas as pd
import pytest
import rasterio
from shapely.geometry import Polygon

from climatoology.base.artifact import ArtifactModality
from ghg_lulc.operator_worker import GHGEmissionFromLULC


def test_plugin_info(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    assert operator.info().name == 'LULC Change Emission Estimation'


def test_plugin_compute(lulc_utility_mock, expected_compute_input, compute_resources):
    operator = GHGEmissionFromLULC(lulc_utility_mock)

    artifacts = operator.compute(compute_resources, expected_compute_input)

    assert {a.name for a in artifacts} == {
        'Carbon stock values per class',
        'Carbon emissions by LULC change type [t]',
        'Change areas and emissions by LULC change type',
        'Change areas by LULC change type [ha]',
        'Classification for first timestamp',
        'Classification for second timestamp',
        'LULC Change',
        'LULC Change (patched)',
        'LULC Emissions',
        'Localised Emissions',
        'Localised Emissions (patched)',
        'Total change areas and emissions in the observation period',
        'Description of the artifacts',
    }

    for artifact in artifacts:
        match artifact.name:
            case 'Classification for first timestamp':
                expected_array = np.array([[[0, 0, 0], [1, 1, 1], [4, 4, 4]]])
                with rasterio.open(artifact.file_path) as src:
                    raster_array = src.read()
                assert_array_equal(raster_array, expected_array)
            case 'Classification for second timestamp':
                expected_array = np.array([[[0, 1, 4], [0, 1, 4], [0, 1, 4]]])
                with rasterio.open(artifact.file_path) as src:
                    raster_array = src.read()
                assert_array_equal(raster_array, expected_array)
            case 'LULC Change':
                expected_array = np.array([[[-1, -1, -1], [-1, 0, 4], [-1, 13, 0]]])
                with rasterio.open(artifact.file_path) as src:
                    raster_array = src.read()
                assert_array_equal(raster_array, expected_array)
            case 'LULC Change (patched)':
                expected_array = np.array([[[0, 0, 0], [0, 1, 2], [0, 3, 1]]])
                with rasterio.open(artifact.file_path) as src:
                    raster_array = src.read()
                assert_array_equal(raster_array, expected_array)
            case 'Localised Emissions':
                expected_array = np.array([[[-999.999, -999.999, -999.999], [-999.999, 0, 1.82], [-999.999, -1.82, 0]]])
                with rasterio.open(artifact.file_path) as src:
                    raster_array = src.read()
                assert_array_equal(raster_array, expected_array)
            case 'Localised Emissions (patched)':
                expected_array = np.array([[[0, 0, 0], [0, 2, 3], [0, 1, 2]]])
                with rasterio.open(artifact.file_path) as src:
                    raster_array = src.read()
                assert_array_equal(raster_array, expected_array)
            case 'LULC Emissions':
                expected_data = geopandas.GeoDataFrame(
                    {
                        'id': ['0', '1'],
                        'color': ['#800000', '#00004c'],
                        'geometry': [
                            Polygon(
                                [
                                    (8.59027496382055, 49.43990950226244),
                                    (8.59027496382055, 49.439819004524885),
                                    (8.590412445730827, 49.439819004524885),
                                    (8.590412445730827, 49.43990950226244),
                                    (8.59027496382055, 49.43990950226244),
                                ]
                            ),
                            Polygon(
                                [
                                    (8.590137481910276, 49.439819004524885),
                                    (8.590137481910276, 49.439728506787326),
                                    (8.59027496382055, 49.439728506787326),
                                    (8.59027496382055, 49.439819004524885),
                                    (8.590137481910276, 49.439819004524885),
                                ]
                            ),
                        ],
                    },
                    crs='EPSG:4326',
                )
                exported_data = geopandas.read_file(artifact.file_path)
                assert_geodataframe_equal(exported_data, expected_data, check_less_precise=True)

            case 'Carbon stock values per class':
                expected_stock_table = pd.DataFrame(
                    {
                        'Class': ['built-up', 'farmland', 'grass', 'forest'],
                        'Definition': ['Sealed surface', 'A farmland', 'A grass patch', 'A forest'],
                        'GHG stock value [t/ha]': [71, 108, 161.5, 253],
                    }
                )
                exported_df = pd.read_csv(artifact.file_path)
                pd.testing.assert_frame_equal(exported_df, expected_stock_table)
            case 'Total change areas and emissions in the observation period':
                data = [
                    ['Area of interest [ha]', 0.8],
                    ['Change share [%]', 2.49],
                    ['Emitting area [ha]', 0.01],
                    ['Emitting area share [%]', 50],
                    ['Sink area [ha]', 0.01],
                    ['Sink area share [%]', 50],
                    ['Total gross emissions [t]', 1.8],
                    ['Total sink [t]', -1.8],
                    ['Net emissions [t]', -0.0],
                ]
                expected_summary = pd.DataFrame(data, columns=['Metric name', 'Value'])
                exported_df = pd.read_csv(artifact.file_path)
                pd.testing.assert_frame_equal(exported_df, expected_summary)
            case 'Change areas and emissions by LULC change type':
                expected_change_type_table = pd.DataFrame(
                    {
                        'Change': ['built-up to forest', 'forest to built-up'],
                        'Area [ha]': [0.01, 0.01],
                        'Total emissions [t]': [-1.83, 1.83],
                    }
                )
                exported_df = pd.read_csv(artifact.file_path)
                pd.testing.assert_frame_equal(exported_df, expected_change_type_table)
            case 'Description of the artifacts':
                with (
                    open('test/resources/artifact_description_test.md', 'r', encoding='utf-8') as expected_description,
                    open(artifact.file_path, 'r') as computed_description,
                ):
                    assert computed_description.read() == expected_description.read()
            case 'Change areas by LULC change type [ha]':
                if artifact.modality == ArtifactModality.CHART:
                    expected_area_data = {
                        'x': ['built-up to forest', 'forest to built-up'],
                        'y': [0.5000004598060519, 0.4999995401939482],
                        'chart_type': 'PIE',
                        'color': ['#00004c', '#800000'],
                    }
                    with open(artifact.file_path) as file:
                        exported_data = json.load(file)
                    assert exported_data == expected_area_data
            case 'Carbon emissions by LULC change type [t]':
                if artifact.modality == ArtifactModality.CHART:
                    expected_emission_data = {
                        'x': ['built-up to forest', 'forest to built-up'],
                        'y': [-1.8250839608794298, 1.8250806041439154],
                        'chart_type': 'BAR',
                        'color': ['#00004c', '#800000'],
                    }
                    with open(artifact.file_path) as file:
                        exported_data = json.load(file)
                    assert exported_data == expected_emission_data
            case _:
                assert False, 'An unexpected artifact was produced.'

            # TODO: Test disabled due to https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/operator-contributions/ghg-emission-from-lulc-change/-/issues/57
            # case 'Localised Emissions':
            #   assert artifact.description == (TEST_RESOURCES_DIR/'localised_emissions_text.md').read_text(encoding='utf-8')


def test_no_change_case(lulc_utility_mock, expected_compute_input, compute_resources):
    lulc_utility_mock.compute_raster.side_effect = [
        rasterio.open(TEST_RESOURCES_DIR / 'minimal_first_ts.tiff'),
        rasterio.open(TEST_RESOURCES_DIR / 'minimal_first_ts.tiff'),
    ]
    operator = GHGEmissionFromLULC(lulc_utility_mock)

    with pytest.raises(ValueError, match='No LULC changes have between detected between the two timestamps.'):
        _ = operator.compute(compute_resources, expected_compute_input)


def test_create_markdown(lulc_utility_mock, expected_compute_input):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    expected_content = (TEST_RESOURCES_DIR / 'artifact_description_test.md').read_text(encoding='utf-8')
    formatted_text = operator.create_markdown(expected_compute_input)
    assert formatted_text == expected_content
