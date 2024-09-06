from numbers import Number
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from climatoology.base.artifact import (
    Chart2dData,
    RasterInfo,
    _Artifact,
    create_chart_artifact,
    create_geotiff_artifact,
    create_markdown_artifact,
    create_table_artifact,
    ContinuousLegendData,
)
from climatoology.base.computation import ComputationResources
from climatoology.utility.api import LabelDescriptor
from pydantic_extra_types.color import Color

from ghg_lulc.utils import PROJECT_DIR, GhgStockSource, RASTER_NO_DATA_VALUE, EMISSION_PER_PIXEL_FACTOR


def create_classification_artifacts(
    lulc_before: RasterInfo,
    lulc_after: RasterInfo,
    labels: Dict[str, LabelDescriptor],
    resources: ComputationResources,
) -> Tuple[_Artifact, _Artifact]:
    # Hack due to https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/web-app/-/issues/114
    unknown_color = Color('gray')
    colormap = lulc_before.colormap
    colormap[0] = unknown_color.as_rgb_tuple()
    legend = {v.name: Color(v.color) for _, v in labels.items()}
    legend['unknown'] = unknown_color

    lulc_before_artifact = create_geotiff_artifact(
        raster_info=RasterInfo(
            data=lulc_before.data.filled(fill_value=RASTER_NO_DATA_VALUE),
            crs=lulc_before.crs,
            transformation=lulc_before.transformation,
            colormap=colormap,
            nodata=RASTER_NO_DATA_VALUE,
        ),
        layer_name='Classification for first timestamp',
        caption='LULC classification at beginning of observation period',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/02_LULC_classifications.md').read_text(
            encoding='utf-8'
        ),
        legend_data=legend,
        resources=resources,
        filename='lulc_classification_before',
        primary=False,
    )

    lulc_after_artifact = create_geotiff_artifact(
        raster_info=RasterInfo(
            data=lulc_after.data.filled(fill_value=RASTER_NO_DATA_VALUE),
            crs=lulc_after.crs,
            transformation=lulc_after.transformation,
            colormap=colormap,
            nodata=RASTER_NO_DATA_VALUE,
        ),
        layer_name='Classification for second timestamp',
        caption='LULC classification at end of observation period',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/02_LULC_classifications.md').read_text(
            encoding='utf-8'
        ),
        legend_data=legend,
        resources=resources,
        filename='lulc_classification_after',
        primary=False,
    )

    return lulc_before_artifact, lulc_after_artifact


def create_change_artifacts(
    change: RasterInfo,
    change_emissions: RasterInfo,
    ghg_stock: pd.DataFrame,
    emission_factors: pd.DataFrame,
    resources: ComputationResources,
) -> Tuple[_Artifact, _Artifact]:
    filled_change_data = change.data.filled(fill_value=RASTER_NO_DATA_VALUE)
    filled_change = RasterInfo(
        data=filled_change_data,
        crs=change.crs,
        transformation=change.transformation,
        colormap=change.colormap,
        nodata=RASTER_NO_DATA_VALUE,
    )
    emission_factors['change'] = emission_factors.apply(
        lambda row: f'{row.utility_class_name_before} to {row.utility_class_name_after}', axis=1
    )
    lookup = emission_factors.set_index('change_id')['change'].to_dict()
    lookup[0] = 'No Change'

    change_artifact = create_geotiff_artifact(
        raster_info=filled_change,
        layer_name='LULC Change',
        caption='LULC changes within the observation period. Note: Transparent pixels within the area of interest'
        'represent areas where the LULC change cannot be derived because the LULC of this pixel cannot be '
        'derived with sufficient confidence in one or both timestamps of the period of analysis.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/03_LULC_change.md').read_text(encoding='utf-8'),
        resources=resources,
        filename='LULC_change',
        legend_data={lookup[change_id]: Color(color) for change_id, color in change.colormap.items()},
        primary=False,
    )

    filled_change_emissions_data = change_emissions.data.filled(fill_value=RASTER_NO_DATA_VALUE)
    change_emission_description = (PROJECT_DIR / 'resources/artifact_descriptions/04_Localized_emissions.md').read_text(
        encoding='utf-8'
    )
    change_emission_description = change_emission_description.format(
        carbon_stocks=ghg_stock[['utility_class_name', 'ghg_stock']].to_markdown(
            index=False,
            headers=['LULC Class', 'Carbon stock [t/ha]'],
            floatfmt='#.1f',
        ),
        emission_factors=emission_factors[
            ['utility_class_name_before', 'utility_class_name_after', 'emission_factor']
        ].to_markdown(
            index=False,
            headers=['From Class', 'To Class', 'Factor [t/ha]'],
            floatfmt='#.1f',
        ),
    )

    patched_change_emissions_data, patched_emissions_colormap = patch_change_data(
        filled_change_emissions_data, change_emissions.colormap
    )

    patched_change_emissions = RasterInfo(
        data=patched_change_emissions_data,
        crs=change.crs,
        transformation=change.transformation,
        colormap=patched_emissions_colormap,
    )

    patched_localised_emission_artifact = create_geotiff_artifact(
        raster_info=patched_change_emissions,
        layer_name='Localised Emissions [t per 100m²]',
        caption='GHG emissions per pixel due to LULC change. Note: Transparent pixels within the area of interest'
        'represent areas where no LULC change emission estimate can be given. The reason for this is either'
        'that the LULC of this pixel cannot be derived with sufficient confidence or that no GHG stock value is'
        'available for the LULC class of this pixel in one or both timestamps of the period of analysis.',
        description=change_emission_description,
        resources=resources,
        filename='LULC_change_emissions_patched',
        legend_data=ContinuousLegendData(
            cmap_name='seismic',
            ticks={
                str(min(emission_factors.emission_factor) * EMISSION_PER_PIXEL_FACTOR): 0,
                str(0): 0.5,
                str(max(emission_factors.emission_factor) * EMISSION_PER_PIXEL_FACTOR): 1,
            },
        ),
        primary=True,
    )

    return change_artifact, patched_localised_emission_artifact


def patch_change_data(change_data: np.ndarray, orig_colormap: Dict[Number, Tuple[int, int, int]]):
    patched_data = change_data.copy()
    patched_colormap = {}
    for key, value in enumerate(np.unique(change_data)):
        patched_data[change_data == value] = key
        patched_colormap[key] = orig_colormap.get(value, Color('black').as_rgb_tuple())

    patched_data = patched_data.astype(np.uint8, copy=False)
    return patched_data, patched_colormap


def create_summary_artifact(summary_df: pd.DataFrame, resources: ComputationResources) -> _Artifact:
    summary_artifact = create_table_artifact(
        data=summary_df,
        title='Summary of results',
        caption='This table shows the gross emissions, gross sinks, and net emissions/sinks in the observation '
        'period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/10a_summary.md').read_text(encoding='utf-8'),
        resources=resources,
        filename='summary',
        primary=True,
    )
    return summary_artifact


def create_area_info_artifact(area_info_df: pd.DataFrame, resources: ComputationResources) -> _Artifact:
    summary_artifact = create_table_artifact(
        data=area_info_df,
        title='Information on the area of interest',
        caption='This table shows the absolute size and the relative proportion with respect to the area of interest'
        'of the change area, emitting area, and sink area in the observation period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/10b_area_info.md').read_text(encoding='utf-8'),
        resources=resources,
        filename='area_info',
        primary=False,
    )
    return summary_artifact


def create_stock_artifact(
    stock_df: pd.DataFrame, stock_source: GhgStockSource, resources: ComputationResources
) -> _Artifact:
    stock_artifact = create_table_artifact(
        data=stock_df,
        title='Carbon stock values per class',
        caption=f'The table contains the carbon stock values for each class according to the selected GHG stock source: {stock_source.value}.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/08_ghg_stocks.md').read_text(encoding='utf-8'),
        resources=resources,
        filename='stock',
        primary=False,
    )
    return stock_artifact


def create_change_type_artifact(change_type_table: pd.DataFrame, resources: ComputationResources) -> _Artifact:
    change_type_table_artifact = create_table_artifact(
        data=change_type_table,
        title='Change areas and emissions by LULC change type',
        caption='This table shows the total change area by LULC change type [ha] and the total change emissions by '
        'LULC change type [t] in the observation period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/09_stats_change_type.md').read_text(
            encoding='utf-8'
        ),
        resources=resources,
        filename='stats_change_type',
        primary=True,
    )
    return change_type_table_artifact


def create_area_plot_artifact(area_data: Chart2dData, resources: ComputationResources) -> _Artifact:
    area_data_artifact = create_chart_artifact(
        data=area_data,
        title='Change areas by LULC change type [ha]',
        caption='This pie chart shows the change areas by LULC change type [ha] in the observation period.',
        resources=resources,
        description=(PROJECT_DIR / 'resources/artifact_descriptions/07_area_plot.md').read_text(encoding='utf-8'),
        filename='area_plot',
        primary=True,
    )
    return area_data_artifact


def create_emission_plot_artifact(emission_data: Chart2dData, resources: ComputationResources) -> _Artifact:
    emission_data_artifact = create_chart_artifact(
        data=emission_data,
        title='Carbon emissions by LULC change type [t]',
        caption='This bar chart shows the carbon emissions by LULC change type [t] in the observation period.',
        resources=resources,
        description=(PROJECT_DIR / 'resources/artifact_descriptions/06_emission_plot.md').read_text(encoding='utf-8'),
        filename='emission_plot',
        primary=True,
    )
    return emission_data_artifact


def create_artifact_description_artifact(formatted_text: str, resources: ComputationResources) -> _Artifact:
    artifact_description_artifact = create_markdown_artifact(
        text=formatted_text,
        name='Description of the artifacts',
        tl_dr='This contains the information you need to understand the artifacts.',
        resources=resources,
        filename='artifact_description',
        primary=False,
    )
    return artifact_description_artifact
