import geopandas as gpd
import pandas as pd
import shapely
from climatoology.base.artifact import Artifact, Chart2dData, ArtifactMetadata
from climatoology.base.artifact_creators import create_chart_artifact, create_table_artifact
from climatoology.base.computation import ComputationResources

from ghg_lulc.components.emissions import EmissionCalculator
from ghg_lulc.components.utils import PROJECT_DIR, Topics, GhgStockSource
from ghg_lulc.core.input import ComputeInput


def create_table_artifacts(
    emission_calculator: EmissionCalculator,
    emissions_df: gpd.GeoDataFrame,
    ghg_stock: pd.DataFrame,
    aoi: shapely.MultiPolygon,
    params: ComputeInput,
    resources: ComputationResources,
) -> list[Artifact]:
    """
    Contains the methods to create the table artifacts.

    :param emission_calculator: Class containing the emission estimation methods
    :param emissions_df: Geodataframe with LULC change polygons and emissions [t] for each change type
    :param ghg_stock: Dataframe with LULC classes, their GHG stocks and additional info
    :param params: Operator input
    :param resources: Ephemeral computation resources
    :return: List of the table artifacts
    """
    ghg_stock_df = EmissionCalculator.filter_ghg_stock(ghg_stock)
    stock_artifact = create_stock_artifact(ghg_stock_df, params.carbon_stock_source, resources)

    emission_info_df, area_info_df = emission_calculator.summary_stats(emissions_df, aoi)
    summary_artifact = create_summary_artifact(emission_info_df, resources)
    area_info_artifact = create_area_info_artifact(area_info_df, resources)

    change_type_df = emission_calculator.get_change_type_table(emissions_df)
    change_type_artifact = create_change_type_artifact(change_type_df, resources)

    return [stock_artifact, summary_artifact, area_info_artifact, change_type_artifact]


def create_chart_artifacts(
    emissions_df: gpd.GeoDataFrame,
    emissions_calculator: EmissionCalculator,
    resources: ComputationResources,
) -> list[Artifact]:
    """
    Contains the methods to create the chart artifacts.

    :param emissions_df: Geodataframe with LULC change polygons and emissions [t] for each change type
    :param emissions_calculator: Class containing the emission estimation methods
    :param resources: Ephemeral computation resources
    :return: List of the chart artifacts
    """
    area_chart_data = emissions_calculator.area_plot(emissions_df)
    area_plot_artifact = create_area_plot_artifact(area_chart_data, resources)

    emission_chart_data = emissions_calculator.emission_plot(emissions_df)
    emission_plot_artifact = create_emission_plot_artifact(emission_chart_data, resources)

    return [area_plot_artifact, emission_plot_artifact]


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
