import json
import numpy as np
from climatoology.utility.exception import ClimatoologyUserError
from numpy.testing import assert_array_equal
import pandas as pd
import pytest
import rasterio
from climatoology.base.artifact import _Artifact, ArtifactModality
from climatoology.base.info import _Info

from ghg_lulc.operator_worker import GHGEmissionFromLULC
from test.conftest import TEST_RESOURCES_DIR


def test_plugin_info_request(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    assert isinstance(operator.info(), _Info)
    assert operator.info().name == 'LULC Change Emission Estimation'


def test_plugin_compute_request(
    lulc_utility_mock, default_aoi, default_aoi_properties, expected_compute_input, compute_resources
):
    operator = GHGEmissionFromLULC(lulc_utility_mock)

    computed_artifacts = operator.compute(
        resources=compute_resources,
        aoi=default_aoi,
        aoi_properties=default_aoi_properties,
        params=expected_compute_input,
    )

    assert len(computed_artifacts) == 11
    for artifact in computed_artifacts:
        assert isinstance(artifact, _Artifact)


def test_no_change_case(
    lulc_utility_mock, default_aoi, default_aoi_properties, expected_compute_input, compute_resources
):
    lulc_utility_mock.compute_raster.side_effect = [
        rasterio.open(TEST_RESOURCES_DIR / 'minimal_first_ts.tiff'),
        rasterio.open(TEST_RESOURCES_DIR / 'minimal_first_ts.tiff'),
    ]
    operator = GHGEmissionFromLULC(lulc_utility_mock)

    with pytest.raises(
        ClimatoologyUserError, match='No land use/land cover changes were detected between the two selected dates'
    ):
        _ = operator.compute(compute_resources, default_aoi, default_aoi_properties, expected_compute_input)


def test_create_markdown(lulc_utility_mock, expected_compute_input):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    expected_content = (TEST_RESOURCES_DIR / 'artifact_description_test.md').read_text(encoding='utf-8')
    formatted_text = operator.create_markdown(expected_compute_input)
    assert formatted_text == expected_content


def test_plugin_compute_result(
    lulc_utility_mock, expected_compute_input, default_aoi, default_aoi_properties, compute_resources
):
    operator = GHGEmissionFromLULC(lulc_utility_mock)

    artifacts = operator.compute(
        resources=compute_resources,
        aoi=default_aoi,
        aoi_properties=default_aoi_properties,
        params=expected_compute_input,
    )

    assert {a.name for a in artifacts} == {
        'Carbon stock values per class',
        'Carbon emissions by LULC change type [t]',
        'Change areas and emissions by LULC change type',
        'Change areas by LULC change type [ha]',
        'Classification for first timestamp',
        'Classification for second timestamp',
        'LULC Change',
        'Localised Emissions [t per 100m²]',
        'Summary of results',
        'Description of the artifacts',
        'Information on the area of interest',
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
                expected_array = np.array([[[255, 255, 255], [255, 0, 4], [255, 13, 0]]])
                with rasterio.open(artifact.file_path) as src:
                    raster_array = src.read()
                assert_array_equal(raster_array, expected_array)
            case 'Localised Emissions [t per 100m²]':
                expected_array = np.array([[[0, 0, 0], [0, 2, 3], [0, 1, 2]]])
                with rasterio.open(artifact.file_path) as src:
                    raster_array = src.read()
                assert_array_equal(raster_array, expected_array)
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
            case 'Summary of results':
                data_summary = [
                    ['Gross Emissions', 1.83],
                    ['Gross Sink', -1.83],
                    ['Net Emissions/Sink', 0],
                ]
                expected_summary = pd.DataFrame(data_summary, columns=['Metric Name', 'Value [t]'])
                expected_summary.set_index('Metric Name', inplace=True)
                exported_df = pd.read_csv(artifact.file_path, index_col=0)
                pd.testing.assert_frame_equal(exported_df, expected_summary)
            case 'Information on the area of interest':
                data_area_info = [
                    ['Area of Interest (AOI)', 0.81, 100.0],
                    ['Change Area', 0.02, 2.49],
                    ['Emitting Area', 0.01, 1.24],
                    ['Sink Area', 0.01, 1.24],
                ]
                expected_area_info = pd.DataFrame(
                    data_area_info, columns=['Metric Name', 'Absolute Value [ha]', 'Proportion of AOI [%]']
                )
                expected_area_info.set_index('Metric Name', inplace=True)
                exported_df = pd.read_csv(artifact.file_path, index_col=0)
                pd.testing.assert_frame_equal(exported_df, expected_area_info)
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
                        'x_unit': None,
                        'y': [0.010027933850985878, 0.01002791540738415],
                        'y_unit': None,
                        'chart_type': 'PIE',
                        'color': ['#3b4cc0', '#b40426'],
                    }
                    with open(artifact.file_path) as file:
                        exported_data = json.load(file)
                    assert exported_data == expected_area_data
            case 'Carbon emissions by LULC change type [t]':
                if artifact.modality == ArtifactModality.CHART:
                    expected_emission_data = {
                        'x': ['built-up to forest', 'forest to built-up'],
                        'x_unit': None,
                        'y': [-1.8250839608794298, 1.8250806041439154],
                        'y_unit': None,
                        'chart_type': 'BAR',
                        'color': ['#808080', '#808080'],
                    }
                    with open(artifact.file_path) as file:
                        exported_data = json.load(file)
                    assert exported_data == expected_emission_data
            case _:
                assert False, 'An unexpected artifact was produced.'
