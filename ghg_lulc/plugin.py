import asyncio
import logging
import os
import uuid
from datetime import date
from pathlib import Path
from typing import List, Optional, Dict

import geojson_pydantic
import numpy as np
import rasterio
import shapely
from climatoology.app.plugin import PlatformPlugin
from climatoology.base.operator import Operator, Info, Artifact, ArtifactModality, Concern, ComputationResources
from climatoology.broker.message_broker import AsyncRabbitMQ
from climatoology.store.object_store import MinioStorage
from climatoology.utility.api import LULCWorkUnit, LulcUtilityUtility
from pydantic import field_validator, model_validator, BaseModel, Field
from semver import Version

from ghg_lulc.emissions import EmissionCalculator

log = logging.getLogger(__name__)
PROJECT_DIR = Path(__file__).parent.parent

EMISSION_FACTORS = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 1.5), (7, 35), (8, 36.5), (9, 119.5), (10, 121), (11, 156)]


class ComputeInput(BaseModel):
    aoi: geojson_pydantic.Feature[
        geojson_pydantic.MultiPolygon,
        Optional[Dict]
    ] = Field(title='Area of Interest',
              description='Area to calculate GHG emissions for. Be aware that the plugin currently works on the '
                          'bounding box of that area!',
              validate_default=True,
              examples=[{
                  "type": "Feature",
                  "properties": {},
                  "geometry": {
                      "type": "MultiPolygon",
                      "coordinates": [
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
              }])

    def get_geom(self) -> shapely.MultiPolygon:
        """Convert the input geojson geometry to a shapely geometry.

        :return: A shapely.MultiPolygon representing the area of interest defined by the user.
        """
        return shapely.geometry.shape(self.aoi.geometry)

    date_1: date = Field(title="Period Start",
                         description='First timestamp of the period of analysis',
                         examples=[date(2018, 5, 1)],
                         gt=date(2017, 1, 1),
                         lt=date.today())
    date_2: date = Field(title="Period End",
                         description='Last timestamp of the period of analysis',
                         examples=[date(2020, 5, 1)],
                         gt=date(2017, 1, 1),
                         lt=date.today())

    @field_validator("date_1", "date_2")
    @classmethod
    def check_month_year(cls, value):
        if not 5 <= value.month <= 9:
            raise ValueError("Dates must be within the months May to September.")
        return value

    @model_validator(mode='after')
    def check_order(self):
        if not self.date_2 > self.date_1:
            raise ValueError("Period start must be before period end.")
        return self


class GHGEmissionFromLULC(Operator[ComputeInput]):
    """A blueprint class to implement your specific operator with a bit more functionality."""

    def __init__(self, lulc_utility: LulcUtilityUtility):
        self.lulc_utility = lulc_utility

    def info(self) -> Info:
        """
        :return: Info object with name, image, version, purpose, methodology, and literature sources.
        """

        return Info(name='LULCChangeEmissionEstimation',
                    icon=PROJECT_DIR / 'resources/icon.jpeg',
                    version=Version(major=0,
                                    minor=0,
                                    patch=1),
                    purpose=(PROJECT_DIR / 'resources/purpose.txt').read_text(),
                    methodology=(PROJECT_DIR / 'resources/methodology.md').read_text(),
                    sources=PROJECT_DIR / 'resources/sources.bib',
                    concerns=[Concern.CLIMATE_ACTION__GHG_EMISSION])

    def compute(self, resources: ComputationResources, params: ComputeInput) -> List[Artifact]:
        """
        :param resources: ephemeral computation resources
        :param params: operator input
        :return: Geotiff of LULC classification in timeframe 1: 'output/LULC_1.tif'
        :return: Geotiff of LULC classification in timeframe 2: 'output/LULC_2.tif'
        :return: Geotiff of LULC changes: 'output/LULC_change.tif'
        :return: Geopackage of LULC changes: 'output/LULC_change_vector.gpkg'
        :return: CSV file with change areas and emissions by LULC change type: 'output/stats_change_type.csv'
        :return: CSV file with summary statistics: 'output/summary.csv'
        :return: PNG file with plot showing change areas by LULC change type: 'output/areas.png'
        :return: PNG file with plot showing emissions by LULC change type: 'output/emissions.png
        """

        emissions_calculator = EmissionCalculator(compute_dir=resources.computation_dir)

        aoi_box = params.get_geom().bounds

        log.info('The Operator report-method was called and will return LULC changes and LULC change emissions in '
                 f'the area: {aoi_box}')

        area1 = LULCWorkUnit(area_coords=aoi_box,
                             end_date=params.date_1.isoformat(),
                             threshold=0)

        area2 = LULCWorkUnit(area_coords=aoi_box,
                             end_date=params.date_2.isoformat(),
                             threshold=0)

        emissions_per_class = [(0, 0),
                               (1, 0),
                               (2, 0),
                               (3, 0),
                               (4, 0),
                               (5, 0),
                               (6, 1.5),
                               (7, 35),
                               (8, 36.5),
                               (9, 119.5),
                               (10, 121),
                               (11, 156)]

        lulc_array1, meta, transform, crs, lulc_tif1 = self.fetch_lulc(resources.computation_dir, area1)
        lulc_array2, meta, transform, crs, lulc_tif2 = self.fetch_lulc(resources.computation_dir, area2)

        changes = emissions_calculator.derive_lulc_changes(lulc_array1, lulc_array2)
        change_file = emissions_calculator.export_raster(changes, meta)
        emission_factor_df = emissions_calculator.convert_raster()
        emission_factor_df = emissions_calculator.allocate_emissions(emission_factor_df, EMISSION_FACTORS)
        total_area = emissions_calculator.calculate_total_change_area(emission_factor_df)
        emission_factor_df, area_df = emissions_calculator.calculate_area_by_change_type(emission_factor_df)
        emission_factor_df = emissions_calculator.calculate_absolute_emissions_per_poly(emission_factor_df)

        change_vector_file = emissions_calculator.export_vector(emission_factor_df)

        total_net_emissions, total_gross_emissions, total_sink = emissions_calculator.calculate_total_emissions(
            emission_factor_df)
        emission_sum_df = emissions_calculator.calculate_emissions_by_change_type(emission_factor_df)
        out_df, change_type_file = emissions_calculator.change_type_stats(area_df, emission_sum_df)

        areas_chart_file = emissions_calculator.area_plot(out_df)

        emission_chart_file = emissions_calculator.emission_plot(out_df)
        summary_file = emissions_calculator.summary_stats(total_area, total_net_emissions, total_gross_emissions,
                                                          total_sink)

        return [Artifact(name='classification_1',
                         modality=ArtifactModality.MAP_LAYER,
                         file_path=lulc_tif1,
                         summary='LULC classification at beginning of observation period',
                         description='LULC classification at beginning of observation period. The classes are forest, '
                                     'agriculture, and settlement.'),
                Artifact(name='classification_2',
                         modality=ArtifactModality.MAP_LAYER,
                         file_path=lulc_tif2,
                         summary='LULC classification at end of observation period',
                         description='LULC classification at end of observation period. The classes are forest, '
                                     'agriculture, and settlement.'),
                Artifact(name='LULC_change',
                         modality=ArtifactModality.MAP_LAYER,
                         file_path=change_file,
                         summary='LULC changes within the observation period',
                         description='LULC changes within the observation period. The raster cell values represent '
                                     'emission factors depending on the LULC change type. Each emission factor '
                                     'represents a certain LULC change type, so the map shows what kind of LULC change '
                                     'happened and at the same time the emissions per ha of these changes.'),
                Artifact(name='LULC_change_vector',
                         modality=ArtifactModality.MAP_LAYER,
                         file_path=change_vector_file,
                         summary='LULC changes within the observation period in vector format',
                         description='LULC changes within the observation period. The emissions per ha values '
                                     'represent the emission factors (carbon emissions per hectare) depending on the '
                                     'LULC change type. Each emission factor represents a certain LULC change type, '
                                     'so the map shows what kind of LULC change happened and at the same time the '
                                     'emissions per ha of these changes. The emissions value represents the absolute '
                                     'carbon emissions of each LULC change polygon.'),
                Artifact(name='stats_change_type',
                         modality=ArtifactModality.TABLE,
                         file_path=change_type_file,
                         summary='change areas and emissions by LULC change type',
                         description='The table contains the total change area by LULC change type and the total '
                                     'change emissions by LULC change type.'),
                Artifact(name='area_plot',
                         modality=ArtifactModality.IMAGE,
                         file_path=areas_chart_file,
                         summary='change areas by LULC change type [ha]',
                         description='pie chart showing the change areas by LULC change type [ha] in the observation '
                                     'period'),
                Artifact(name='emission_plot',
                         modality=ArtifactModality.IMAGE,
                         file_path=emission_chart_file,
                         summary='carbon emissions by LULC change type [t]',
                         description='horizontal bar chart showing the carbon emissions by LULC change type [t] in the '
                                     'observation period'),
                Artifact(name='summary',
                         modality=ArtifactModality.TABLE,
                         file_path=summary_file,
                         summary='total net emissions, gross emissions, and carbon sink in the observation period',
                         description='Net emissions are the combination of emissions and carbon sinks, gross emissions '
                                     'are the total LULC change emissions of carbon to the atmosphere, and carbon sink '
                                     'means the total sequestration of carbon as a result of LULC change.')]

    def fetch_lulc(self, compute_dir, area):
        with self.lulc_utility.compute_raster([area]) as lulc_classification:
            lulc_array = lulc_classification.read()
            crs = lulc_classification.crs
            transform = lulc_classification.transform
            rows = lulc_array.shape[1]
            cols = lulc_array.shape[2]
            lulc_array = lulc_array.reshape([rows, cols])

        meta = {
            "driver": "GTiff",
            "dtype": np.int8,
            "count": 1,
            "width": cols,
            "height": rows,
            "transform": transform,
            "crs": crs
        }

        lulc_tif = compute_dir / f'LULC_{uuid.uuid4()}.tif'

        with rasterio.open(lulc_tif, "w", **meta) as dst:
            dst.write(lulc_array, 1)

        return lulc_array, meta, transform, crs, lulc_tif


async def start_plugin() -> None:
    """ Function to start the plugin within the architecture.

    Please adjust the class reference to the class you created above. Apart from that **DO NOT TOUCH**.

    :return:
    """

    lulc_utility = LulcUtilityUtility(host=os.environ.get('LULC_HOST'),
                                      port=int(os.environ.get('LULC_PORT')),
                                      root_url=os.environ.get('LULC_ROOT_URL'))
    operator = GHGEmissionFromLULC(lulc_utility)
    log.info(f'Configuring plugin: {operator.info().name}')

    storage = MinioStorage(host=os.environ.get('MINIO_HOST'),
                           port=int(os.environ.get('MINIO_PORT')),
                           access_key=os.environ.get('MINIO_ACCESS_KEY'),
                           secret_key=os.environ.get('MINIO_SECRET_KEY'),
                           bucket=os.environ.get('MINIO_BUCKET'),
                           secure=os.environ.get('MINIO_SECURE') == 'True')
    broker = AsyncRabbitMQ(host=os.environ.get('RABBITMQ_HOST'),
                           port=int(os.environ.get('RABBITMQ_PORT')),
                           user=os.environ.get('RABBITMQ_USER'),
                           password=os.environ.get('RABBITMQ_PASSWORD'))

    await broker.async_init()
    log.info(f'Configuring async broker: {os.environ.get("RABBITMQ_HOST")}')

    plugin = PlatformPlugin(operator=GHGEmissionFromLULC(lulc_utility),
                            storage=storage,
                            broker=broker)
    log.info(f'Running plugin: {operator.info().name}')
    await plugin.run()


if __name__ == '__main__':
    asyncio.run(start_plugin())
