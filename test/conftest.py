import os
import uuid
from unittest.mock import patch

import pytest
import rasterio
from climatoology.base.computation import ComputationScope
from climatoology.utility.api import LabelDescriptor

from ghg_lulc.input import ComputeInput


@pytest.fixture
def expected_compute_input() -> ComputeInput:
    return ComputeInput(aoi={'type': 'Feature',
                             'properties': {},
                             'geometry': {
                                 'type': 'MultiPolygon',
                                 'coordinates': [
                                     [
                                         [
                                             [8.59, 49.36],
                                             [8.78, 49.36],
                                             [8.78, 49.44],
                                             [8.59, 49.44],
                                             [8.59, 49.36]
                                         ]
                                     ]
                                 ]
                             }
                             },
                        date_before='2022-05-17',
                        date_after='2023-05-31')


@pytest.fixture
def compute_resources():
    with ComputationScope(uuid.uuid4()) as resources:
        yield resources


@pytest.fixture
def lulc_utility_mock():
    with patch('climatoology.utility.api.LulcUtility') as lulc_utility:
        lulc_utility.compute_raster.side_effect = [
            rasterio.open(f'{os.path.dirname(__file__)}/resources/minimal_first_ts.tiff'),
            rasterio.open(f'{os.path.dirname(__file__)}/resources/minimal_second_ts.tiff')]

        lulc_utility.get_class_legend.return_value = {'unknown': LabelDescriptor(name='unknown',
                                                                                 description='unknown',
                                                                                 osm_filter=None,
                                                                                 raster_value=0,
                                                                                 color=(0, 0, 0)),
                                                      'forest': LabelDescriptor(name='forest',
                                                                                description='A forest',
                                                                                osm_filter='landuse=forest',
                                                                                raster_value=1,
                                                                                color=(255, 255, 255)),
                                                      'grass': LabelDescriptor(name='grass',
                                                                               description='A grass patch',
                                                                               osm_filter='landuse=grass',
                                                                               raster_value=2,
                                                                               color=(254, 255, 255)),
                                                      'farmland': LabelDescriptor(name='farmland',
                                                                                  description='A farmland',
                                                                                  osm_filter='landuse=farmland',
                                                                                  raster_value=3,
                                                                                  color=(253, 255, 255)),
                                                      'built-up': LabelDescriptor(name='built-up',
                                                                                  description='Sealed surface',
                                                                                  osm_filter='landuse=residential',
                                                                                  raster_value=4,
                                                                                  color=(252, 255, 255)),
                                                      'permanent-crops': LabelDescriptor(name='permanent-crops',
                                                                                         description='permanent crops',
                                                                                         osm_filter='landuse=vineyard',
                                                                                         raster_value=5,
                                                                                         color=(251, 255, 255)),
                                                      'water': LabelDescriptor(name='water',
                                                                               description='water',
                                                                               osm_filter='natural=water',
                                                                               raster_value=6,
                                                                               color=(250, 255, 255)),
                                                      }

        yield lulc_utility
