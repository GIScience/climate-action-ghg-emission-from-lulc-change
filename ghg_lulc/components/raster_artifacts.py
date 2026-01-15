from numbers import Number
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from climatoology.base.artifact import RasterInfo, Artifact, ContinuousLegendData, ArtifactMetadata, Legend
from climatoology.base.artifact_creators import create_raster_artifact
from climatoology.base.computation import ComputationResources
from climatoology.utility.lulc import LabelDescriptor
from pydantic_extra_types.color import Color

from ghg_lulc.components.utils import (
    PROJECT_DIR,
    RASTER_NO_DATA_VALUE,
    EMISSION_PER_PIXEL_FACTOR,
    Topics,
)


def create_classification_artifacts(
    lulc_before: RasterInfo,
    lulc_after: RasterInfo,
    labels: Dict[str, LabelDescriptor],
    resources: ComputationResources,
) -> Tuple[Artifact, Artifact]:
    # Hack due to https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/web-app/-/issues/114
    unknown_color = Color('gray')
    lulc_before.colormap[0] = unknown_color.as_rgb_tuple()
    lulc_after.colormap[0] = unknown_color.as_rgb_tuple()
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
        raster_info=lulc_before,
        legend=Legend(legend_data=legend),
        metadata=lulc_before_metadata,
        resources=resources,
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
        raster_info=lulc_after,
        legend=Legend(legend_data=legend),
        metadata=lulc_after_metadata,
        resources=resources,
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
