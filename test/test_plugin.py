import os
import uuid
from unittest.mock import patch

import pytest
import rasterio
from climatoology.base.computation import ComputationScope

from ghg_lulc.plugin import GHGEmissionFromLULC, ComputeInput


@pytest.fixture
def lulc_utility_mock():
    with patch('climatoology.utility.api.LulcUtilityUtility') as lulc_utility:
        lulc_utility.compute_raster.side_effect = [rasterio.open(f'{os.path.dirname(__file__)}/test_1.tif'), rasterio.open(f'{os.path.dirname(__file__)}/test_2.tif')]

        yield lulc_utility


def test_plugin_info(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    assert operator.info().name == 'LULCChangeEmissionEstimation'


def test_plugin_compute(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    operator_input = ComputeInput(aoi={'type': 'Feature',
                                       'properties': {},
                                       'geometry': {
                                           'type': 'MultiPolygon',
                                           'coordinates': [
                                               [
                                                   [
                                                       [12.3, 48.22],
                                                       [12.3, 48.34],
                                                       [12.48, 48.34],
                                                       [12.48, 48.22],
                                                       [12.3, 48.22]
                                                   ]
                                               ]
                                           ]
                                       }
                                       },
                                  date_1='2018-05-01',
                                  date_2='2023-06-01')

    with ComputationScope(uuid.uuid4()) as resources:
        artifacts = operator.compute(resources, operator_input)

        assert {a.name for a in artifacts} == {'classification_1', 'classification_2', 'LULC_change',
                                               'LULC_change_vector', 'Change areas and emissions by LULC change type',
                                               'Total net emissions, gross emissions, and carbon sink in the '
                                               'observation period', 'Change areas by LULC change type [ha]',
                                               'Carbon emissions by LULC change type [t]'}
