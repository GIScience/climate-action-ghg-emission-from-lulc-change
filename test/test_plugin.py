import uuid
from unittest.mock import patch

import pytest
import rasterio
from climatoology.base.operator import ComputationScope

from plugin.plugin import GHGEmissionFromLULC, ComputeInput


@pytest.fixture
def lulc_utility_mock():
    with patch('climatoology.utility.api.LulcUtilityUtility') as lulc_utility:
        lulc_utility.compute_raster.side_effect = [rasterio.open('test_1.tif'), rasterio.open('test_2.tif')]

        yield lulc_utility


def test_plugin_info(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    assert operator.info().name == 'LULCChangeEmissionEstimation'


def test_plugin_compute(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    operator_input = ComputeInput(area_coords=(12.304687500000002,
                                               48.2246726495652,
                                               12.480468750000002,
                                               48.3416461723746),
                                  start_date_1="2018-05-01",
                                  end_date_1="2018-06-01",
                                  start_date_2="2023-05-01",
                                  end_date_2="2023-06-01")

    with ComputationScope(uuid.uuid4()) as resources:
        artifacts = operator.compute(resources, operator_input)

        assert {a.name for a in artifacts} == {'classification_1', 'classification_2', 'LULC_change', 'LULC_change_vector', 'stats_change_type', 'summary', 'area_plot', 'emission_plot'}
