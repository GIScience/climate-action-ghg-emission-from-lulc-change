from numbers import Number
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from climatoology.base.artifact import Chart2dData, RasterInfo, Artifact, ContinuousLegendData, ArtifactMetadata, Legend
from climatoology.base.artifact_creators import create_raster_artifact, create_table_artifact, create_chart_artifact
from climatoology.base.computation import ComputationResources
from climatoology.utility.lulc import LabelDescriptor
from pydantic_extra_types.color import Color

from ghg_lulc.utils import PROJECT_DIR, GhgStockSource, RASTER_NO_DATA_VALUE, EMISSION_PER_PIXEL_FACTOR, Topics


def create_classification_artifacts(
    lulc_before: RasterInfo,
    lulc_after: RasterInfo,
    labels: Dict[str, LabelDescriptor],
    resources: ComputationResources,
) -> Tuple[Artifact, Artifact]:
    # Hack due to https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/web-app/-/issues/114
    unknown_color = Color('gray')
    colormap = lulc_before.colormap
    colormap[0] = unknown_color.as_rgb_tuple()
    legend = {v.name: Color(v.color) for _, v in labels.items()}
    legend['unknown'] = unknown_color

    lulc_before_metadata = ArtifactMetadata(
        name='Classification for period start',
        filename='lulc_classification_before',
        summary='LULC classification at the start of the analysis period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/02_LULC_classifications.md').read_text(
            encoding='utf-8'
        ),
        tags={Topics.MAPS},
    )
    lulc_before_artifact = create_raster_artifact(
        raster_info=RasterInfo(
            data=lulc_before.data.filled(fill_value=RASTER_NO_DATA_VALUE),
            crs=lulc_before.crs,
            transformation=lulc_before.transformation,
            colormap=colormap,
        ),
        legend=Legend(legend_data=legend),
        resources=resources,
        metadata=lulc_before_metadata,
    )

    lulc_after_metadata = ArtifactMetadata(
        name='Classification for period end',
        filename='lulc_classification_after',
        summary='LULC classification at the end of the analysis period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/02_LULC_classifications.md').read_text(
            encoding='utf-8'
        ),
        tags={Topics.MAPS},
    )
    lulc_after_artifact = create_raster_artifact(
        raster_info=RasterInfo(
            data=lulc_after.data.filled(fill_value=RASTER_NO_DATA_VALUE),
            crs=lulc_after.crs,
            transformation=lulc_after.transformation,
            colormap=colormap,
        ),
        legend=Legend(legend_data=legend),
        resources=resources,
        metadata=lulc_after_metadata,
    )

    return lulc_before_artifact, lulc_after_artifact


def create_change_artifacts(
    change: RasterInfo,
    change_emissions: RasterInfo,
    ghg_stock: pd.DataFrame,
    emission_factors: pd.DataFrame,
    resources: ComputationResources,
) -> Tuple[Artifact, Artifact]:
    filled_change_data = change.data.filled(fill_value=RASTER_NO_DATA_VALUE)
    filled_change = RasterInfo(
        data=filled_change_data,
        crs=change.crs,
        transformation=change.transformation,
        colormap=change.colormap,
    )
    emission_factors['change'] = emission_factors.apply(
        lambda row: f'{row.utility_class_name_before} to {row.utility_class_name_after}', axis=1
    )
    lookup = emission_factors.set_index('change_id')['change'].to_dict()
    lookup[0] = 'No Change'

    change_metadata = ArtifactMetadata(
        name='LULC Change',
        filename='LULC_change',
        summary='LULC changes within the analysis period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/03_LULC_change.md').read_text(encoding='utf-8'),
        tags={Topics.MAPS},
    )
    change_artifact = create_raster_artifact(
        raster_info=filled_change,
        resources=resources,
        legend=Legend(legend_data={lookup[change_id]: Color(color) for change_id, color in change.colormap.items()}),
        metadata=change_metadata,
    )

    filled_change_emissions_data = change_emissions.data.filled(fill_value=RASTER_NO_DATA_VALUE)
    change_emission_description = (PROJECT_DIR / 'resources/artifact_descriptions/04_Localized_emissions.md').read_text(
        encoding='utf-8'
    )
    change_emission_description = change_emission_description.format(
        carbon_stocks=ghg_stock[['utility_class_name', 'ghg_stock']].to_markdown(
            index=False,
            headers=['LULC Class', 'Carbon stock (tonnes/ha)'],
            floatfmt='#.1f',
        ),
        emission_factors=emission_factors[
            ['utility_class_name_before', 'utility_class_name_after', 'emission_factor']
        ].to_markdown(
            index=False,
            headers=['From Class', 'To Class', 'Factor (tonnes/ha)'],
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

    patched_localised_emission_metadata = ArtifactMetadata(
        name='Localised carbon flows (tonnes per 100m²)',
        filename='LULC_change_emissions_patched',
        summary='Carbon flows per pixel due to LULC change. Note: Transparent pixels within the area of interest '
        'represent areas where carbon flows from LULC change could not be estimated, either because the pixels could '
        'not be classified with sufficient confidence or they were classified as "permanent crops" or "water", for '
        'which no carbon stock values are available.',
        description=change_emission_description,
        tags={Topics.MAPS},
    )
    patched_localised_emission_artifact = create_raster_artifact(
        raster_info=patched_change_emissions,
        resources=resources,
        legend=Legend(
            legend_data=ContinuousLegendData(
                cmap_name='coolwarm',
                ticks={
                    str(min(emission_factors.emission_factor) * EMISSION_PER_PIXEL_FACTOR): 0,
                    str(0): 0.5,
                    str(max(emission_factors.emission_factor) * EMISSION_PER_PIXEL_FACTOR): 1,
                },
            ),
        ),
        metadata=patched_localised_emission_metadata,
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


def create_summary_artifact(summary_df: pd.DataFrame, resources: ComputationResources) -> Artifact:
    summary_metadata = ArtifactMetadata(
        name='Summary of results',
        filename='summary',
        summary='Gross emissions, gross sinks, and net emissions/sinks in the analysis period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/10a_summary.md').read_text(encoding='utf-8'),
        tags={Topics.TABLES},
    )
    summary_artifact = create_table_artifact(
        data=summary_df,
        resources=resources,
        metadata=summary_metadata,
    )
    return summary_artifact


def create_area_info_artifact(area_info_df: pd.DataFrame, resources: ComputationResources) -> Artifact:
    area_info_metadata = ArtifactMetadata(
        name='Summary of detected changes',
        filename='area_info',
        summary='Size of the area classified as a carbon source, carbon sink, and total LULC change during the period '
        'of analysis.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/10b_area_info.md').read_text(encoding='utf-8'),
        tags={Topics.TABLES},
    )
    summary_artifact = create_table_artifact(
        data=area_info_df,
        resources=resources,
        metadata=area_info_metadata,
    )
    return summary_artifact


def create_stock_artifact(
    stock_df: pd.DataFrame, stock_source: GhgStockSource, resources: ComputationResources
) -> Artifact:
    stock_metadata = ArtifactMetadata(
        name='Carbon stock values per class',
        filename='stock',
        summary=f'Carbon stock values for each class according to: {stock_source.value}',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/08_ghg_stocks.md').read_text(encoding='utf-8'),
        tags={Topics.TABLES},
    )
    stock_artifact = create_table_artifact(
        data=stock_df,
        resources=resources,
        metadata=stock_metadata,
    )
    return stock_artifact


def create_change_type_artifact(change_type_table: pd.DataFrame, resources: ComputationResources) -> Artifact:
    change_type_metadata = ArtifactMetadata(
        name='Change areas and carbon flows by LULC change type',
        filename='stats_change_type',
        summary='Total change area by LULC change type (ha) and total carbon flows by '
        'LULC change type (tonnes) in the analysis period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/09_stats_change_type.md').read_text(
            encoding='utf-8'
        ),
        tags={Topics.TABLES},
    )
    change_type_table_artifact = create_table_artifact(
        data=change_type_table,
        resources=resources,
        metadata=change_type_metadata,
    )
    return change_type_table_artifact


def create_area_plot_artifact(area_data: Chart2dData, resources: ComputationResources) -> Artifact:
    area_data_metadata = ArtifactMetadata(
        name='Change areas by LULC change type (ha)',
        filename='area_plot',
        summary='Change areas by LULC change type (ha) in the analysis period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/07_area_plot.md').read_text(encoding='utf-8'),
        tags={Topics.CHARTS},
    )
    area_data_artifact = create_chart_artifact(
        data=area_data,
        resources=resources,
        metadata=area_data_metadata,
    )
    return area_data_artifact


def create_emission_plot_artifact(emission_data: Chart2dData, resources: ComputationResources) -> Artifact:
    emission_data_metadata = ArtifactMetadata(
        name='Carbon flows by LULC change type (tonnes)',
        filename='emission_plot',
        summary='Carbon flows by LULC change type (tonnes) in the analysis period.',
        description=(PROJECT_DIR / 'resources/artifact_descriptions/06_emission_plot.md').read_text(encoding='utf-8'),
        tags={Topics.CHARTS},
    )
    emission_data_artifact = create_chart_artifact(
        data=emission_data,
        resources=resources,
        metadata=emission_data_metadata,
    )
    return emission_data_artifact
