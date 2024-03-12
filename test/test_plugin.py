from test.conftest import TEST_RESOURCES_DIR

import pandas as pd
import pytest
import rasterio

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
        'Total net emissions, gross emissions, and carbon sink in the observation period',
        'Description of the artifacts',
    }

    for artifact in artifacts:
        match artifact.name:
            case 'Change areas and emissions by LULC change type':
                expected_change_type_table = pd.DataFrame(
                    {
                        'Change': ['farmland to built-up', 'grass to farmland', 'forest to grass'],
                        'Area [ha]': [0.01, 0.01, 0.01],
                        'Total emissions [t]': [0.37, 0.54, 0.92],
                    }
                )
                exported_df = pd.read_csv(artifact.file_path)
                pd.testing.assert_frame_equal(exported_df, expected_change_type_table)
            # TODO: Test disabled due to https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/operator-contributions/ghg-emission-from-lulc-change/-/issues/57
            # case 'Localised Emissions':
            #    assert artifact.description == (TEST_RESOURCES_DIR/'localised_emissions_text.md').read_text(encoding='utf-8')


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
