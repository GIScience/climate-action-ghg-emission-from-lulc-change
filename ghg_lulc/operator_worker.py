import logging
from typing import List, Tuple

import geopandas as gpd
import pandas as pd
from climatoology.base.artifact import RasterInfo, _Artifact
from climatoology.base.operator import Concern, Info, Operator, PluginAuthor
from climatoology.utility.api import LulcUtility, LulcWorkUnit
from semver import Version

from ghg_lulc.artifact import (
    ComputationResources,
    create_area_plot_artifacts,
    create_artifact_description_artifact,
    create_change_artifacts,
    create_change_type_artifact,
    create_classification_artifacts,
    create_emission_plot_artifacts,
    create_emissions_artifact,
    create_stock_artifact,
    create_summary_artifact,
)
from ghg_lulc.emissions import EmissionCalculator
from ghg_lulc.input import ComputeInput
from ghg_lulc.utils import PROJECT_DIR, calc_emission_factors, fetch_lulc, get_ghg_stock

log = logging.getLogger(__name__)


class GHGEmissionFromLULC(Operator[ComputeInput]):
    def __init__(self, lulc_utility: LulcUtility):
        self.lulc_utility = lulc_utility
        self.ghg_stock = get_ghg_stock(self.lulc_utility.get_class_legend())
        self.emission_factors = calc_emission_factors(self.ghg_stock)

    def info(self) -> Info:
        """
        :return: Info object with name, image, version, purpose, methodology, and literature sources.
        """
        return Info(
            name='LULC Change Emission Estimation',
            icon=PROJECT_DIR / 'resources/icon.jpeg',
            authors=[
                PluginAuthor(
                    name='Veit Ulrich',
                    affiliation='GIScience Research Group at the Institute of Geography, Heidelberg University',
                    website='https://www.geog.uni-heidelberg.de/gis/ulrich.html',
                ),
                PluginAuthor(
                    name='Moritz Schott',
                    affiliation='HeiGIT gGmbH',
                    website='https://heigit.org/heigit-team',
                ),
            ],
            version=str(Version(major=0, minor=0, patch=1)),
            purpose=(PROJECT_DIR / 'resources/purpose.md').read_text(),
            methodology=(PROJECT_DIR / 'resources/methodology.md').read_text(),
            sources=PROJECT_DIR / 'resources/sources.bib',
            concerns=[Concern.CLIMATE_ACTION__GHG_EMISSION],
        )

    def compute(self, resources: ComputationResources, params: ComputeInput) -> List[_Artifact]:
        """
        :param resources: ephemeral computation resources
        :param params: operator input
        :return: List of produced artifacts
        """
        emission_calculator = EmissionCalculator(
            emission_factors=self.emission_factors[params.ghg_stock_source], resources=resources
        )

        change_df, change_artifacts = self.get_changes(emission_calculator, params, resources)

        emissions_df = emission_calculator.calculate_absolute_emissions_per_poly(change_df)
        emissions_artifact = create_emissions_artifact(emissions_df, resources)

        table_artifacts = create_table_artifacts(
            emission_calculator,
            emissions_df,
            self.ghg_stock[params.ghg_stock_source],
            params,
            resources,
        )

        chart_artifacts = create_chart_artifacts(
            emissions_df,
            emission_calculator,
            resources,
        )
        formatted_text = self.create_markdown(params)
        artifact_description_artifact = create_artifact_description_artifact(formatted_text, resources)

        return (
            change_artifacts
            + [emissions_artifact]
            + table_artifacts
            + chart_artifacts
            + [artifact_description_artifact]
        )

    def get_changes(
        self,
        emission_calculator: EmissionCalculator,
        params: ComputeInput,
        resources: ComputationResources,
    ) -> Tuple[gpd.GeoDataFrame, List[_Artifact]]:
        lulc_before, lulc_after = self.get_classifications(params)

        classification_artifacts = create_classification_artifacts(
            lulc_before,
            lulc_after,
            resources,
        )

        change_raster, change_emissions_raster = emission_calculator.derive_lulc_changes(lulc_before, lulc_after)
        change_artifacts = create_change_artifacts(
            change_raster,
            change_emissions_raster,
            self.ghg_stock[params.ghg_stock_source],
            self.emission_factors[params.ghg_stock_source],
            resources,
        )

        change_df = emission_calculator.convert_change_raster(change_raster)

        return change_df, [*classification_artifacts, *change_artifacts]

    def get_classifications(self, params: ComputeInput) -> Tuple[RasterInfo, RasterInfo]:
        aoi_box = params.get_geom().bounds
        aoi = params.get_geom()

        area_before = LulcWorkUnit(
            area_coords=aoi_box,
            end_date=params.date_before,
            threshold=params.classification_threshold,
        )
        area_after = LulcWorkUnit(
            area_coords=aoi_box,
            end_date=params.date_after,
            threshold=params.classification_threshold,
        )

        lulc_before = fetch_lulc(self.lulc_utility, area_before, aoi)
        lulc_after = fetch_lulc(self.lulc_utility, area_after, aoi)

        return lulc_before, lulc_after

    def create_markdown(self, params: ComputeInput) -> str:
        directory = PROJECT_DIR / 'resources/artifact_descriptions'
        content = [file.read_text(encoding='utf-8') for file in sorted(directory.glob('*.md'))]
        content = '\n\n'.join(content)
        carbon_stocks = self.ghg_stock[params.ghg_stock_source][['utility_class_name', 'ghg_stock']].to_markdown(
            index=False, headers=['LULC Class', 'Carbon stock [t/ha]'], floatfmt='#.1f'
        )
        emission_factors = self.emission_factors[params.ghg_stock_source][
            [
                'utility_class_name_before',
                'utility_class_name_after',
                'emission_factor',
            ]
        ].to_markdown(
            index=False,
            headers=[
                'From Class',
                'To Class',
                'Factor [t/ha]',
            ],
            floatfmt='#.1f',
        )
        formatted_text = content.format(
            date_before=params.date_before,
            date_after=params.date_after,
            classification_threshold=params.classification_threshold * 100,
            carbon_stocks=carbon_stocks,
            emission_factors=emission_factors,
        )

        return formatted_text


def create_table_artifacts(
    emission_calculator: EmissionCalculator,
    emissions_df: gpd.GeoDataFrame,
    ghg_stock: pd.DataFrame,
    params: ComputeInput,
    resources: ComputationResources,
) -> List[_Artifact]:
    ghg_stock_df = EmissionCalculator.filter_ghg_stock(ghg_stock)
    stock_artifact = create_stock_artifact(ghg_stock_df, params.ghg_stock_source, resources)

    summary_df = EmissionCalculator.summary_stats(emissions_df, params.get_geom())
    summary_artifact = create_summary_artifact(summary_df, resources)

    change_type_df = emission_calculator.get_change_type_table(emissions_df)
    change_type_artifact = create_change_type_artifact(change_type_df, resources)

    return [stock_artifact, summary_artifact, change_type_artifact]


def create_chart_artifacts(
    emissions_df: gpd.GeoDataFrame,
    emissions_calculator: EmissionCalculator,
    resources: ComputationResources,
) -> List[_Artifact]:
    area_chart_data, areas_chart_file = emissions_calculator.area_plot(emissions_df)
    area_plot_artifacts = create_area_plot_artifacts(area_chart_data, areas_chart_file, resources)

    emission_chart_data, emission_chart_file = emissions_calculator.emission_plot(emissions_df)
    emission_plot_artifacts = create_emission_plot_artifacts(emission_chart_data, emission_chart_file, resources)

    return [*area_plot_artifacts, *emission_plot_artifacts]
