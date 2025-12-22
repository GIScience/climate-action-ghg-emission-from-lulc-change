import logging
from datetime import timedelta, datetime
from pathlib import Path
from typing import List, Tuple

import geopandas as gpd
import pandas as pd
import shapely
from climatoology.base.artifact import RasterInfo
from climatoology.base.baseoperator import BaseOperator, Artifact, AoiProperties
from climatoology.base.computation import ComputationResources
from climatoology.base.plugin_info import (
    generate_plugin_info,
    PluginInfo,
    PluginAuthor,
    Concern,
    PluginState,
    CustomAOI,
)
from climatoology.utility.lulc import LulcUtility, LulcWorkUnit, FusionMode
from climatoology.base.exception import ClimatoologyUserError
from pydantic import HttpUrl

from ghg_lulc.artifact import (
    create_area_plot_artifact,
    create_change_artifacts,
    create_change_type_artifact,
    create_classification_artifacts,
    create_emission_plot_artifact,
    create_stock_artifact,
    create_summary_artifact,
    create_area_info_artifact,
)
from ghg_lulc.emissions import EmissionCalculator
from ghg_lulc.input import ComputeInput
from ghg_lulc.utils import (
    PROJECT_DIR,
    calc_emission_factors,
    fetch_lulc,
    get_ghg_stock,
    reproject_aoi,
    GERMANY_BBOX_4326,
    CLASSIFICATION_THRESHOLD,
)

log = logging.getLogger(__name__)


class GHGEmissionFromLULC(BaseOperator[ComputeInput]):
    def __init__(self, lulc_utility: LulcUtility):
        super().__init__()
        self.lulc_utility = lulc_utility
        self.ghg_stock = get_ghg_stock(self.lulc_utility.get_class_legend().osm)
        self.emission_factors = calc_emission_factors(self.ghg_stock)

    def info(self) -> PluginInfo:
        """
        :return: Info object with information about the plugin.
        """
        return generate_plugin_info(
            name='LULC Change',
            icon=PROJECT_DIR / 'resources/icon.jpeg',
            state=PluginState.HIBERNATE,
            authors=[
                PluginAuthor(
                    name='Veit Ulrich',
                    affiliation='HeiGIT gGmbH',
                    website=HttpUrl('https://heigit.org/heigit-team'),
                ),
                PluginAuthor(
                    name='Moritz Schott',
                    affiliation='HeiGIT gGmbH',
                    website=HttpUrl('https://heigit.org/heigit-team'),
                ),
                PluginAuthor(
                    name='Maciej Adamiak',
                    affiliation='HeiGIT gGmbH',
                    website=HttpUrl('https://heigit.org/heigit-team'),
                ),
                PluginAuthor(
                    name='Maria Martin',
                    affiliation='HeiGIT gGmbH',
                    website=HttpUrl('https://heigit.org/heigit-team'),
                ),
                PluginAuthor(
                    name='Sven Lautenbach',
                    affiliation='HeiGIT gGmbH',
                    website=HttpUrl('https://heigit.org/heigit-team'),
                ),
            ],
            purpose=Path(PROJECT_DIR / 'resources/purpose.md'),
            teaser='Assess the carbon flows from Land Use and Land Cover (LULC) change during a given period in any area within Germany.',
            methodology=Path(PROJECT_DIR / 'resources/methodology.md'),
            sources_library=PROJECT_DIR / 'resources/sources.bib',
            concerns={Concern.CLIMATE_ACTION__GHG_EMISSION},
            computation_shelf_life=timedelta(weeks=52),
            demo_input_parameters=ComputeInput(start_year=2017, end_year=2024),
            demo_aoi=CustomAOI(name='Grünheide Demo', path=Path(PROJECT_DIR / 'resources/gruenheide.geojson')),
        )

    def compute(  # dead: disable
        self,
        resources: ComputationResources,
        aoi: shapely.MultiPolygon,
        aoi_properties: AoiProperties,
        params: ComputeInput,
    ) -> List[Artifact]:
        """
        Main method of the operator.

        :param aoi_properties: Name and ID of the AOI
        :param aoi: Area of interest
        :param resources: Ephemeral computation resources
        :param params: Operator input
        :return: List of produced artifacts
        """

        trained_region_bbox = GERMANY_BBOX_4326

        if not aoi.intersects(trained_region_bbox):
            raise ClimatoologyUserError('The selected area is outside of Germany. Please select an area within Germany')

        aoi_utm32n = reproject_aoi(aoi)
        aoi_utm32n_area_km2 = round(aoi_utm32n.area / 1000000, 2)

        if aoi_utm32n_area_km2 > 1000:
            raise ClimatoologyUserError(
                f'The selected area is too large: {aoi_utm32n_area_km2} km². Currently, the maximum allowed area is 1000 km². Please select a smaller area or a sub-region of your selected area'
            )

        emission_calculator = EmissionCalculator(
            emission_factors=self.emission_factors[params.carbon_stock_source], resources=resources
        )

        change_df, change_artifacts = self.get_changes(emission_calculator, aoi, params, resources)

        emissions_df = emission_calculator.calculate_absolute_emissions_per_poly(change_df)

        table_artifacts = create_table_artifacts(
            emission_calculator,
            emissions_df,
            self.ghg_stock[params.carbon_stock_source],
            aoi,
            params,
            resources,
        )

        chart_artifacts = create_chart_artifacts(
            emissions_df,
            emission_calculator,
            resources,
        )

        return change_artifacts + table_artifacts + chart_artifacts

    def get_changes(
        self,
        emission_calculator: EmissionCalculator,
        aoi: shapely.MultiPolygon,
        params: ComputeInput,
        resources: ComputationResources,
    ) -> Tuple[gpd.GeoDataFrame, List[Artifact]]:
        """
        Get LULC classifications and LULC changes.

        :param aoi: Area of interest
        :param emission_calculator: Class containing the emission estimation methods
        :param params: Operator input
        :param resources: Ephemeral computation resources
        :return: Geodataframe with LULC change polygons dissolved by change type and emission factors
        :return: LULC classification artifacts at first and second timestamp
        :return: Artifacts containing a raster with LULC changes and a raster with pixel-wise emissions
        """
        lulc_before, lulc_after = self.get_classifications(aoi, params)

        classification_artifacts = create_classification_artifacts(
            lulc_before,
            lulc_after,
            self.lulc_utility.get_class_legend().osm,
            resources,
        )

        change_raster, change_emissions_raster = emission_calculator.derive_lulc_changes(lulc_before, lulc_after)
        change_artifacts = create_change_artifacts(
            change_raster,
            change_emissions_raster,
            self.ghg_stock[params.carbon_stock_source],
            self.emission_factors[params.carbon_stock_source],
            resources,
        )

        change_df = emission_calculator.convert_change_raster(change_raster)

        return change_df, [*classification_artifacts, *change_artifacts]

    def get_classifications(self, aoi: shapely.MultiPolygon, params: ComputeInput) -> Tuple[RasterInfo, RasterInfo]:
        """
        Get LULC classifications in the AOI at first and second timestamp.

        :param aoi: Area of interest
        :param params: Operator input
        :return: RasterInfo objects with LULC classifications at first and second timestamp
        """

        area_before = LulcWorkUnit(
            aoi=aoi,
            start_date=datetime(params.start_year, 7, 1),
            end_date=datetime(params.start_year, 7, 31),
            threshold=CLASSIFICATION_THRESHOLD,
            fusion_mode=FusionMode.ONLY_MODEL,
        )
        area_after = LulcWorkUnit(
            aoi=aoi,
            start_date=datetime(params.end_year, 7, 1),
            end_date=datetime(params.end_year, 7, 31),
            threshold=CLASSIFICATION_THRESHOLD,
            fusion_mode=FusionMode.ONLY_MODEL,
        )

        lulc_before = fetch_lulc(self.lulc_utility, area_before, aoi)
        lulc_after = fetch_lulc(self.lulc_utility, area_after, aoi)

        return lulc_before, lulc_after


def create_table_artifacts(
    emission_calculator: EmissionCalculator,
    emissions_df: gpd.GeoDataFrame,
    ghg_stock: pd.DataFrame,
    aoi: shapely.MultiPolygon,
    params: ComputeInput,
    resources: ComputationResources,
) -> List[Artifact]:
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
) -> List[Artifact]:
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
