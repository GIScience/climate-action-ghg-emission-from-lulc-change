from numbers import Number
from pathlib import Path
from typing import Tuple, Dict

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image
from climatoology.base.artifact import _Artifact, RasterInfo, create_geotiff_artifact, create_geojson_artifact, \
    create_table_artifact, Chart2dData, create_chart_artifact, create_image_artifact
from climatoology.base.computation import ComputationResources

from ghg_lulc.utils import get_colors, GhgStockSource


def create_classification_artifacts(lulc_before: RasterInfo,
                                    lulc_after: RasterInfo,
                                    resources: ComputationResources) -> Tuple[_Artifact, _Artifact]:
    no_data_value = 0

    lulc_before_artifact = create_geotiff_artifact(
        raster_info=RasterInfo(data=lulc_before.data.filled(fill_value=no_data_value),
                               crs=lulc_before.crs,
                               transformation=lulc_before.transformation,
                               colormap=lulc_before.colormap,
                               nodata=no_data_value),
        layer_name='Classification for first timestamp',
        caption='LULC classification at beginning of observation period',
        description='LULC classification at beginning of observation period. The '
                    'classes are forest, agriculture, and settlement. The '
                    'classification is created using a deep learning model.',
        resources=resources,
        filename='lulc_classification_before')

    lulc_after_artifact = create_geotiff_artifact(
        raster_info=RasterInfo(data=lulc_after.data.filled(fill_value=no_data_value),
                               crs=lulc_after.crs,
                               transformation=lulc_after.transformation,
                               colormap=lulc_after.colormap,
                               nodata=no_data_value),
        layer_name='Classification for second timestamp',
        caption='LULC classification at end of observation period',
        description='LULC classification at end of observation period. The '
                    'classes are forest, agriculture, and settlement. The '
                    'classification is created using a deep learning model.',
        resources=resources,
        filename='lulc_classification_after')

    return lulc_before_artifact, lulc_after_artifact


def create_change_artifacts(change: RasterInfo,
                            change_emissions: RasterInfo,
                            resources: ComputationResources) -> Tuple[_Artifact, _Artifact, _Artifact, _Artifact]:
    no_data_value = -1
    filled_change_data = change.data.filled(fill_value=no_data_value)
    filled_change = RasterInfo(data=filled_change_data,
                               crs=change.crs,
                               transformation=change.transformation,
                               colormap=change.colormap,
                               nodata=no_data_value)
    change_artifact = create_geotiff_artifact(
        raster_info=filled_change,
        layer_name='LULC Change',
        caption='LULC changes within the observation period',
        description='LULC changes within the observation period.',
        resources=resources,
        filename='LULC_change')

    patched_change_data, patched_colormap = patch_change_data(filled_change_data, change.colormap)
    patched_change = RasterInfo(data=patched_change_data,
                                crs=change.crs,
                                transformation=change.transformation,
                                colormap=patched_colormap)

    patched_change_artifact = create_geotiff_artifact(
        raster_info=patched_change,
        layer_name='LULC Change (patched)',
        caption='LULC changes within the observation period',
        description='LULC changes within the observation period.',
        resources=resources,
        filename='LULC_change_patched')

    no_data_value = -999.999
    filled_change_emissions_data = change_emissions.data.filled(fill_value=no_data_value)
    filled_change_emissions = RasterInfo(data=filled_change_emissions_data,
                                         crs=change.crs,
                                         transformation=change.transformation,
                                         colormap=change_emissions.colormap,
                                         nodata=no_data_value)
    localised_emission_artifact = create_geotiff_artifact(
        raster_info=filled_change_emissions,
        layer_name='Localised Emissions',
        caption='GHG emissions per pixel due to LULC change',
        description='Absolute GHG emissions per pixel [t] due to LULC change within the'
                    'observation period. A pixel size of 10 m is assumed.',
        resources=resources,
        filename='LULC_change_emissions')

    patched_change_emissions_data, patched_emissions_colormap = patch_change_data(filled_change_emissions_data,
                                                                                  change_emissions.colormap)

    patched_change_emissions = RasterInfo(data=patched_change_emissions_data,
                                          crs=change.crs,
                                          transformation=change.transformation,
                                          colormap=patched_emissions_colormap)

    patched_localised_emission_artifact = create_geotiff_artifact(
        raster_info=patched_change_emissions,
        layer_name='Localised Emissions (patched)',
        caption='GHG emissions per pixel due to LULC change',
        description='Absolute GHG emissions per pixel [t] due to LULC change within the'
                    'observation period. A pixel size of 10 m is assumed.',
        resources=resources,
        filename='LULC_change_emissions_patched')

    return change_artifact, patched_change_artifact, localised_emission_artifact, patched_localised_emission_artifact


def patch_change_data(change_data: np.ndarray, orig_colormap: Dict[Number, Tuple[int, int, int]]):
    patched_data = change_data.copy()
    patched_colormap = {}
    for key, value in enumerate(np.unique(change_data)):
        patched_data[change_data == value] = key
        patched_colormap[key] = orig_colormap.get(value)

    patched_data = patched_data.astype(np.uint16, copy=False)
    return patched_data, patched_colormap


def create_emissions_artifact(emissions_df: gpd.GeoDataFrame, resources: ComputationResources) -> _Artifact:
    colors = get_colors(emissions_df['emissions']).to_list()
    emissions_artifact = create_geojson_artifact(features=emissions_df['geometry'],
                                                 layer_name='LULC Emissions',
                                                 caption='Absolute carbon emissions of LULC changes within the observation '
                                                         'period per change type [t]',
                                                 resources=resources,
                                                 description='LULC change emissions within the observation period. The polygons '
                                                             'are colored by their absolute carbon emissions or sinks during '
                                                             'the observation period. Each polygon represents one type of change '
                                                             '(e.g. grass to farmland) and is aggregated over the whole area of interst.',
                                                 color=colors,
                                                 filename='LULC_emissions')
    return emissions_artifact


def create_summary_artifact(summary_df: gpd, resources: ComputationResources) -> _Artifact:
    summary_artifact = create_table_artifact(data=summary_df,
                                             title='Total net emissions, gross emissions, and carbon sink in the observation '
                                                   'period',
                                             caption='The table contains the total net emissions, gross emissions, and carbon '
                                                     'sink in the observation period.',
                                             description='Net emissions are the combination of emissions and carbon sinks, '
                                                         'gross emissions are the total LULC change emissions of carbon to the'
                                                         'atmosphere, and carbon sink means the total sequestration of carbon'
                                                         'as a result of LULC change.',
                                             resources=resources,
                                             filename='summary')
    return summary_artifact


def create_stock_artifact(stock_df: pd.DataFrame,
                          stock_source: GhgStockSource,
                          resources: ComputationResources) -> _Artifact:
    stock_artifact = create_table_artifact(data=stock_df,
                                           title='Carbon stock values per class',
                                           caption=f'The table contains the carbon stock values for each class according to the selected {stock_source.value}.',
                                           description='The table contains three columns: The class name, the class definition and the GHG stock value for the respective class.',
                                           resources=resources,
                                           filename='stock')
    return stock_artifact


def create_change_type_artifact(change_type_table: pd.DataFrame, resources: ComputationResources) -> _Artifact:
    change_type_table_artifact = create_table_artifact(data=change_type_table,
                                                       title='Change areas and emissions by LULC change type',
                                                       caption='The table contains the total change area by LULC change type and the '
                                                               'total change emissions by LULC change type.',
                                                       description='description',
                                                       resources=resources,
                                                       filename='stats_change_type')
    return change_type_table_artifact


def create_area_plot_artifacts(area_data: Chart2dData,
                               area_file: Path,
                               resources: ComputationResources) -> Tuple[_Artifact, _Artifact]:
    area_data_artifact = create_chart_artifact(data=area_data,
                                               title='Change areas by LULC change type [ha]',
                                               caption='This pie chart shows the change areas by LULC change type [ha] in the '
                                                       'observation period.',
                                               resources=resources,
                                               description='description',
                                               filename='area_plot')
    area_image_artifact = create_image_artifact(image=Image.open(area_file),
                                                title='Change areas by LULC change type [ha]',
                                                caption='This pie chart shows the change areas by LULC change type [ha] in the '
                                                        'observation period.',
                                                resources=resources,
                                                description='description',
                                                filename='area_plot')
    return area_data_artifact, area_image_artifact


def create_emission_plot_artifacts(emission_data: Chart2dData,
                                   emission_file: Path,
                                   resources: ComputationResources) -> Tuple[_Artifact, _Artifact]:
    emission_data_artifact = create_chart_artifact(data=emission_data,
                                                   title='Carbon emissions by LULC change type [t]',
                                                   caption='This bar chart shows the carbon emissions by LULC change'
                                                           'type [t] in the observation period.',
                                                   resources=resources,
                                                   description='description',
                                                   filename='emission_plot')
    emission_image_artifact = create_image_artifact(image=Image.open(emission_file),
                                                    title='Carbon emissions by LULC change type [t]',
                                                    caption='This bar chart shows the carbon emissions by LULC change'
                                                            'type [t] in the observation period.',
                                                    resources=resources,
                                                    description='description',
                                                    filename='emission_plot')
    return emission_data_artifact, emission_image_artifact
