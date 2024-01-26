import os
import uuid
from unittest.mock import patch

from affine import Affine
import numpy as np
from pyproj import CRS
import pytest
import rasterio
from shapely.geometry import Polygon
from climatoology.base.computation import ComputationScope
from climatoology.utility.api import LULCWorkUnit
from ghg_lulc.plugin import GHGEmissionFromLULC, ComputeInput


@pytest.fixture
def lulc_utility_mock():
    with patch('climatoology.utility.api.LulcUtilityUtility') as lulc_utility:
        lulc_utility.compute_raster.side_effect = [rasterio.open(f'{os.path.dirname(__file__)}/test_0.tif'),
                                                   rasterio.open(f'{os.path.dirname(__file__)}/test_1.tif'),
                                                   rasterio.open(f'{os.path.dirname(__file__)}/test_2.tif')]

        yield lulc_utility


def test_fetch_lulc(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    lulc_area = LULCWorkUnit(area_coords=(12.3, 48.22, 12.48, 48.34),
                             end_date='2022-05-17',
                             threshold=0)
    aoi = Polygon([(0, 0), (3, 0), (3, -3), (0, -3)])
    expected_array = np.array([[0, 1, 2],
                               [3, 4, 5],
                               [0, 1, 2]])

    expected_meta = {
                'driver': 'GTiff',
                'dtype': np.int8,
                'count': 1,
                'width': 3,
                'height': 3,
                'transform': Affine(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
                'crs': CRS.from_epsg(4326)
    }
    expected_transform = Affine(1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    expected_crs = CRS.from_epsg(4326)
    expected_colors = {i: (255, 0, 0, 255) if i == 1
                       else (0, 255, 0, 255) if i == 2
                       else (0, 0, 255, 255) if i == 3
                       else (130, 130, 0, 255) if i == 4
                       else (130, 0, 130, 255) if i == 5
                       else (0, 0, 0, 255) for i in range(256)}
    lulc_output = operator.fetch_lulc(lulc_area, aoi)
    assert np.array_equal(expected_array, lulc_output.lulc_array)
    assert lulc_output.meta == expected_meta
    assert lulc_output.transform == expected_transform
    assert lulc_output.crs == expected_crs
    assert lulc_output.colormap == expected_colors


def test_plugin_info(lulc_utility_mock):
    operator = GHGEmissionFromLULC(lulc_utility_mock)
    assert operator.info().name == 'LULC Change Emission Estimation'


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
                                                       [12.4, 48.3],
                                                       [12.3, 48.22]
                                                   ]
                                               ]
                                           ]
                                       }
                                       },
                                  date_1='2022-05-17',
                                  date_2='2023-05-31')

    lulc_area = LULCWorkUnit(area_coords=(12.3, 48.22, 12.48, 48.34),
                             end_date='2022-05-17',
                             threshold=0)
    aoi = Polygon([(0, 0), (3, 0), (3, -3), (0, -3)])
    operator.fetch_lulc(lulc_area, aoi)

    with ComputationScope(uuid.uuid4()) as resources:
        artifacts = operator.compute(resources, operator_input)

        assert {a.name for a in artifacts} == {'Classification 1', 'Classification 2', 'LULC Change',
                                               'LULC Emissions', 'Change areas and emissions by LULC change type',
                                               'Total net emissions, gross emissions, and carbon sink in the '
                                               'observation period', 'Change areas by LULC change type [ha]',
                                               'Carbon emissions by LULC change type [t]'}