from climatoology.base.exception import ClimatoologyUserError
import pytest
import rasterio
from climatoology.base.artifact import Artifact
from climatoology.base.plugin_info import PluginInfo

from ghg_lulc.core.operator_worker import GHGEmissionFromLULC
from test.conftest import TEST_RESOURCES_DIR


def test_plugin_info_request(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    assert isinstance(operator.info(), PluginInfo)
    assert operator.info().name == 'LULC Change'


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

    assert len(computed_artifacts) == 10
    for artifact in computed_artifacts:
        assert isinstance(artifact, Artifact)


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

    assert len(artifacts) == 10
    for artifact in artifacts:
        assert isinstance(artifact, Artifact)
