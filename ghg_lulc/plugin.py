import asyncio
import logging.config
from datetime import date
from pathlib import Path
from typing import List, Optional, Dict

import geojson_pydantic
import numpy as np
import shapely
import yaml
from PIL import Image
from climatoology.app.plugin import PlatformPlugin
from climatoology.base.artifact import create_geotiff_artifact, create_geojson_artifact, \
    create_table_artifact, create_image_artifact, create_chart_artifact, RasterInfo
from climatoology.base.operator import Operator, Info, _Artifact, Concern, ComputationResources, PluginAuthor
from climatoology.broker.message_broker import AsyncRabbitMQ
from climatoology.store.object_store import MinioStorage
from climatoology.utility.api import LulcWorkUnit, LulcUtility
from pydantic import condate, confloat
from pydantic import field_validator, model_validator, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rasterio.features import geometry_mask
from semver import Version

from ghg_lulc.emissions import EmissionCalculator

log_config = 'conf/logging.yaml'
log = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent

EMISSION_FACTORS = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 1.5), (7, 35), (8, 36.5), (9, 119.5), (10, 121),
                    (11, 156), (12, -156), (13, -121), (14, -119.5), (15, -36.5), (16, -35), (17, -1.5)]
PLOT_COLORS = {'settlement to forest': 'midnightblue', 'farmland to forest': 'mediumblue',
               'meadow to forest': 'blue', 'settlement to meadow': 'royalblue',
               'settlement to farmland': 'cornflowerblue', 'farmland to meadow': 'lightsteelblue',
               'meadow to farmland': 'mistyrose', 'farmland to settlement': 'pink',
               'meadow to settlement': 'lightcoral', 'forest to meadow': 'indianred',
               'forest to farmland': 'firebrick', 'forest to settlement': 'darkred'}


class Settings(BaseSettings):
    log_level: str = 'INFO'

    minio_host: str
    minio_port: int
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False

    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_user: str
    rabbitmq_password: str

    lulc_host: str
    lulc_port: int
    lulc_path: str

    model_config = SettingsConfigDict(env_file='.env')


class ComputeInput(BaseModel):
    aoi: geojson_pydantic.Feature[
        geojson_pydantic.MultiPolygon,
        Optional[Dict]
    ] = Field(title='Area of Interest',
              description='Area to calculate GHG emissions for. Be aware that the plugin currently works on the '
                          'bounding box of that area!',
              validate_default=True,
              examples=[{
                  'type': 'Feature',
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
              }])
    date_1: condate(ge=date(2017, 1, 1),
                    le=date.today()) = Field(title='Period Start',
                                             description='First timestamp of the period of analysis',
                                             examples=[date(2022, 5, 17)])
    date_2: condate(ge=date(2017, 1, 1),
                    le=date.today()) = Field(title='Period End',
                                             description='Last timestamp of the period of analysis',
                                             examples=[date(2023, 5, 31)])
    classification_threshold: Optional[confloat(ge=0,
                                                le=100)] = Field(title='Minimum required classification confidence [%]',
                                                                 description='The LULC classification by a ML model '
                                                                             'has inherent uncertainties. This number '
                                                                             'defines the minimum level of confidence '
                                                                             'required by the user. Any prediction '
                                                                             "where the model's confidence lies above "
                                                                             'this threshold will be assumed to be '
                                                                             '"true", all classification exhibiting '
                                                                             'lower confidence will be classified as '
                                                                             '"unknown".',
                                                                 examples=[75],
                                                                 default=75)

    def get_geom(self) -> shapely.MultiPolygon:
        """Convert the input geojson geometry to a shapely geometry.

        :return: A shapely.MultiPolygon representing the area of interest defined by the user.
        """
        return shapely.geometry.shape(self.aoi.geometry)

    @field_validator('date_1', 'date_2')
    def check_month_year(cls, value):
        if not 5 <= value.month <= 9:
            raise ValueError('Dates must be within the months May to September.')
        return value

    @model_validator(mode='after')
    def check_order(self):
        if not self.date_2 > self.date_1:
            raise ValueError('Period start must be before period end.')
        return self


class GHGEmissionFromLULC(Operator[ComputeInput]):
    """A blueprint class to implement your specific operator with a bit more functionality."""

    def __init__(self, lulc_utility: LulcUtility):
        self.lulc_utility = lulc_utility

    def info(self) -> Info:
        """
        :return: Info object with name, image, version, purpose, methodology, and literature sources.
        """

        return Info(name='LULC Change Emission Estimation',
                    icon=PROJECT_DIR / 'resources/icon.jpeg',
                    authors=[PluginAuthor(name='Veit Ulrich',
                                          affiliation='GIScience Research Group at the Institute of Geography, '
                                                      'Heidelberg University',
                                          website='https://www.geog.uni-heidelberg.de/gis/ulrich.html')],
                    version=str(Version(major=0,
                                        minor=0,
                                        patch=1)),
                    purpose=(PROJECT_DIR / 'resources/purpose.txt').read_text(),
                    methodology=(PROJECT_DIR / 'resources/methodology.md').read_text(),
                    sources=PROJECT_DIR / 'resources/sources.bib',
                    concerns=[Concern.CLIMATE_ACTION__GHG_EMISSION])

    def compute(self, resources: ComputationResources, params: ComputeInput) -> List[_Artifact]:
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
        aoi = params.get_geom()

        log.info('The Operator report-method was called and will return LULC changes and LULC change emissions in '
                 f'the area: {aoi_box}')

        area1 = LulcWorkUnit(area_coords=aoi_box,
                             end_date=params.date_1.isoformat(),
                             threshold=params.classification_threshold / 100)

        area2 = LulcWorkUnit(area_coords=aoi_box,
                             end_date=params.date_2.isoformat(),
                             threshold=params.classification_threshold / 100)

        lulc_output1 = self.fetch_lulc(area1, aoi)
        lulc_output2 = self.fetch_lulc(area2, aoi)

        changes, change_colormap = emissions_calculator.derive_lulc_changes(np.array(lulc_output1.data),
                                                                            np.array(lulc_output2.data))
        change_raster = RasterInfo(data=changes,
                                   crs=lulc_output1.crs,
                                   transformation=lulc_output1.transformation,
                                   colormap=change_colormap)
        emission_factor_df = emissions_calculator.convert_raster(change_raster)
        emission_factor_df = emissions_calculator.allocate_emissions(emission_factor_df, EMISSION_FACTORS)
        total_area = emissions_calculator.calculate_total_change_area(emission_factor_df)
        emission_factor_df, area_df = emissions_calculator.calculate_area_by_change_type(emission_factor_df)
        emission_factor_df = emissions_calculator.calculate_absolute_emissions_per_poly(emission_factor_df)
        color_col = emissions_calculator.add_colormap(emission_factor_df['emissions'])
        emission_factor_df['color'] = color_col

        total_net_emissions, total_gross_emissions, total_sink = emissions_calculator.calculate_total_emissions(
            emission_factor_df)
        emission_sum_df = emissions_calculator.calculate_emissions_by_change_type(emission_factor_df)
        out_df = emissions_calculator.change_type_stats(area_df, emission_sum_df)

        area_chart_data, areas_chart_file = emissions_calculator.area_plot(out_df, PLOT_COLORS)
        emission_chart_data, emission_chart_file = emissions_calculator.emission_plot(out_df, PLOT_COLORS)
        summary = emissions_calculator.summary_stats(total_area, total_net_emissions, total_gross_emissions, total_sink)

        out_df.set_index('LULC change type', inplace=True)
        area_plot = Image.open(areas_chart_file)
        emission_plot = Image.open(emission_chart_file)

        return [create_geotiff_artifact(raster_info=lulc_output1,
                                        layer_name='Classification 1',
                                        caption='LULC classification at beginning of observation period',
                                        description='LULC classification at beginning of observation period. The '
                                                    'classes are forest, agriculture, and settlement. The '
                                                    'classification is created using a deep learning model.',
                                        resources=resources,
                                        filename='lulc_classification_1'),
                create_geotiff_artifact(raster_info=lulc_output2,
                                        layer_name='Classification 2',
                                        caption='LULC classification at end of observation period',
                                        description='LULC classification at end of observation period. The '
                                                    'classes are forest, agriculture, and settlement. The '
                                                    'classification is created using a deep learning model.',
                                        resources=resources,
                                        filename='lulc_classification_2'),
                create_geotiff_artifact(raster_info=change_raster,
                                        layer_name='LULC Change',
                                        caption='LULC changes within the observation period',
                                        description='LULC changes within the observation period. The raster cell values'
                                                    'are defined in the file methodology.md.',
                                        resources=resources,
                                        filename='LULC_change'),
                create_geojson_artifact(features=emission_factor_df['geometry'],
                                        layer_name='LULC Emissions',
                                        caption='Absolute carbon emissions of LULC change areas within the observation '
                                                'period [t]',
                                        resources=resources,
                                        description='LULC change emissions within the observation period. The polygons '
                                                    'are colored by their absolute carbon emissions or sinks during '
                                                    'the observation period.',
                                        color=emission_factor_df['color'].to_list(),
                                        filename='LULC_emissions'),
                create_table_artifact(data=out_df,
                                      title='Change areas and emissions by LULC change type',
                                      caption='The table contains the total change area by LULC change type and the '
                                              'total change emissions by LULC change type.',
                                      description='description',
                                      resources=resources,
                                      filename='stats_change_type'),
                create_table_artifact(data=summary,
                                      title='Total net emissions, gross emissions, and carbon sink in the observation '
                                            'period',
                                      caption='The table contains the total net emissions, gross emissions, and carbon '
                                              'sink in the observation period.',
                                      description='Net emissions are the combination of emissions and carbon sinks, '
                                                  'gross emissions are the total LULC change emissions of carbon to the'
                                                  'atmosphere, and carbon sink means the total sequestration of carbon'
                                                  'as a result of LULC change.',
                                      resources=resources,
                                      filename='summary'),
                create_chart_artifact(data=area_chart_data,
                                      title='Change areas by LULC change type [ha]',
                                      caption='This pie chart shows the change areas by LULC change type [ha] in the '
                                              'observation period.',
                                      resources=resources,
                                      description='description',
                                      filename='area_plot'),
                create_chart_artifact(data=emission_chart_data,
                                      title='Carbon emissions by LULC change type [t]',
                                      caption='This bar chart shows the carbon emissions by LULC change'
                                              'type [t] in the observation period.',
                                      resources=resources,
                                      description='description',
                                      filename='emission_plot'),
                create_image_artifact(image=area_plot,
                                      title='Change areas by LULC change type [ha]',
                                      caption='This pie chart shows the change areas by LULC change type [ha] in the '
                                              'observation period.',
                                      resources=resources,
                                      description='description',
                                      filename='area_plot'),
                create_image_artifact(image=emission_plot,
                                      title='Carbon emissions by LULC change type [t]',
                                      caption='This bar chart shows the carbon emissions by LULC change'
                                              'type [t] in the observation period.',
                                      resources=resources,
                                      description='description',
                                      filename='emission_plot')
                ]

    def fetch_lulc(self, lulc_area: LulcWorkUnit, aoi: shapely.MultiPolygon) -> RasterInfo:
        with self.lulc_utility.compute_raster([lulc_area]) as lulc_classification:
            lulc_array = lulc_classification.read()
            crs = lulc_classification.crs
            transform = lulc_classification.transform
            colormap = lulc_classification.colormap(1)

        rows = lulc_array.shape[1]
        cols = lulc_array.shape[2]
        lulc_array = lulc_array.reshape([rows, cols])

        mask = ~geometry_mask([aoi], (rows, cols), transform=transform, invert=True)
        lulc_array = np.ma.masked_array(lulc_array, mask)

        lulc_output = RasterInfo(data=lulc_array,
                                 crs=crs,
                                 transformation=transform,
                                 colormap=colormap)

        return lulc_output


async def start_plugin(settings: Settings) -> None:
    """ Function to start the plugin within the architecture.

    Please adjust the class reference to the class you created above. Apart from that **DO NOT TOUCH**.

    :return:
    """

    lulc_utility = LulcUtility(host=settings.lulc_host,
                               port=settings.lulc_port,
                               path=settings.lulc_path)
    operator = GHGEmissionFromLULC(lulc_utility)
    log.info(f'Configuring plugin: {operator.info().name}')

    storage = MinioStorage(host=settings.minio_host,
                           port=settings.minio_port,
                           access_key=settings.minio_access_key,
                           secret_key=settings.minio_secret_key,
                           bucket=settings.minio_bucket,
                           secure=settings.minio_secure)
    broker = AsyncRabbitMQ(host=settings.rabbitmq_host,
                           port=settings.rabbitmq_port,
                           user=settings.rabbitmq_user,
                           password=settings.rabbitmq_password)

    await broker.async_init()
    log.debug(f'Configured broker: {settings.rabbitmq_host} and storage: {settings.minio_host}')

    plugin = PlatformPlugin(operator=GHGEmissionFromLULC(lulc_utility),
                            storage=storage,
                            broker=broker)
    log.info(f'Running plugin: {operator.info().name}')
    await plugin.run()


if __name__ == '__main__':
    settings = Settings()

    logging.basicConfig(level=settings.log_level.upper())
    with open(log_config) as file:
        logging.config.dictConfig(yaml.safe_load(file))
    log.info('Starting Plugin')

    asyncio.run(start_plugin(settings))
