import logging
from typing import Tuple

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyproj
import shapely
from climatoology.base.artifact import Chart2dData, ChartType, RasterInfo
from climatoology.base.computation import ComputationResources
from numpy import ma
from pydantic_extra_types.color import Color
from rasterio.features import shapes
from shapely.ops import transform

from ghg_lulc.utils import SQM_TO_HA, pyplot_to_pydantic_color, EMISSION_PER_PIXEL_FACTOR, RASTER_NO_DATA_VALUE

log = logging.getLogger(__name__)


class EmissionCalculator:
    def __init__(self, emission_factors: pd.DataFrame, resources: ComputationResources):
        self.emission_factors = emission_factors
        self.resources = resources

    def derive_lulc_changes(
        self,
        lulc_before: RasterInfo,
        lulc_after: RasterInfo,
    ) -> Tuple[RasterInfo, RasterInfo]:
        """
        :param lulc_before: LULC classification of first time stamp
        :param lulc_after: LULC classification of second time stamp
        :return: a raster with LULC changes and a raster with pixel-wise emissions
        between first and second time stamp
        """
        log.debug('Deriving LULC changes')

        changes_info = self.get_change_info(lulc_before, lulc_after)

        change_emissions_info = self.get_change_emissions_info(changes_info)

        return changes_info, change_emissions_info

    def get_change_info(
        self,
        lulc_before: RasterInfo,
        lulc_after: RasterInfo,
        unknown_change_value: int = RASTER_NO_DATA_VALUE,
        no_change_value: int = 0,
    ) -> RasterInfo:
        """
        Get LULC changes between first and second time stamp.

        This will return a RasterInfo object with all information necessary to create a geotiff artifact showing LULC
        changes (including color map).

        :param lulc_before: LULC classification of first time stamp
        :param lulc_after: LULC classification of second time stamp
        :param unknown_change_value: Integer to indicate pixels with unknown changes
        :param no_change_value: Integer to indicate no change pixels
        :return: a raster with LULC changes between first and second time stamp
        """
        changes = np.full_like(lulc_before.data, fill_value=unknown_change_value, dtype=np.uint16)

        for row in self.emission_factors.itertuples():
            changes[
                (lulc_before.data == row.raster_value_before) & (lulc_after.data == row.raster_value_after)
            ] = row.change_id

        changes[
            np.logical_and(lulc_before.data == lulc_after.data, lulc_before.data != no_change_value)
        ] = no_change_value

        cmap = plt.get_cmap('tab20b')
        changes_colormap = {}

        change_classes = np.unique(ma.compressed(changes))
        unknown_index = np.argwhere(change_classes == unknown_change_value)
        change_classes = np.delete(change_classes, unknown_index)
        for change_class in change_classes:
            pyplot_color = cmap(change_class / max(change_classes))
            changes_colormap[change_class] = pyplot_to_pydantic_color(pyplot_color).as_rgb_tuple()
        changes_colormap[no_change_value] = Color('gray').as_rgb_tuple()

        return RasterInfo(
            data=changes,
            crs=lulc_before.crs,
            transformation=lulc_before.transformation,
            colormap=changes_colormap,
            nodata=unknown_change_value,
        )

    def get_change_emissions_info(self, changes: RasterInfo, unknown_emissions_value: float = -999.999) -> RasterInfo:
        """
        Get pixel-wise LULC change emissions between first and second time stamp.

        This will return a RasterInfo object with all information necessary to create a geotiff artifact showing
        pixel-wise LULC change emissions (including color map).

        :param changes: a raster with LULC changes between first and second time stamp
        :param unknown_emissions_value: a float value to indicate pixels with unknown emissions
        :return: a raster with pixel-wise emissions between first and second time stamp
        """
        change_emissions = np.full_like(changes.data, fill_value=unknown_emissions_value, dtype=np.floating)

        emissions_colormap = {}
        for row in self.emission_factors.itertuples():
            pixel_emissions = row.emission_factor * EMISSION_PER_PIXEL_FACTOR

            change_emissions[changes.data == row.change_id] = pixel_emissions
            emissions_colormap[pixel_emissions] = row.color.as_rgb_tuple()
        change_emissions[changes.data == 0] = 0

        return RasterInfo(
            data=change_emissions,
            crs=changes.crs,
            transformation=changes.transformation,
            colormap=emissions_colormap,
            nodata=unknown_emissions_value,
        )

    def convert_change_raster(self, change_raster: RasterInfo) -> gpd.GeoDataFrame:
        """
        Convert the LULC change raster to a geodataframe and reproject it to the local UTM
        coordinate system, so we can perform area-based calculations on it.

        :param change_raster: a raster with LULC changes between first and second time stamp
        :return: geodataframe with LULC change polygons dissolved by change type and emission factors
        """
        log.debug(
            f'Converting change raster of shape {change_raster.data.shape} with dtype '
            f'{change_raster.data.dtype} to vector'
        )

        results = (
            {'properties': {'change_id': int(value)}, 'geometry': geometry}
            for geometry, value in shapes(change_raster.data, mask=None, transform=change_raster.transformation)
        )
        org_df = gpd.GeoDataFrame.from_features(results, crs=change_raster.crs)

        org_df = org_df.dissolve(by='change_id', as_index=False)
        org_df = pd.merge(left=org_df, right=self.emission_factors, on='change_id')

        if org_df.empty:
            raise ValueError('No LULC changes have between detected between the two timestamps.')

        target_utm = org_df.estimate_utm_crs()
        log.debug(f'Reprojecting geodataframe from {change_raster.crs} to {target_utm.name}')
        emission_factor_df = org_df.to_crs(target_utm)

        return emission_factor_df

    @staticmethod
    def calculate_absolute_emissions_per_poly(change_df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Calculate absolute LULC change emissions per LULC change type [t].

        :param change_df: geodataframe with LULC change polygon and emission factor [t/ha] for each change type
        :return: geodataframe with additional absolute emissions column
        """
        change_df = change_df.copy()
        change_df['emissions'] = change_df.area * SQM_TO_HA * change_df['emission_factor']

        return change_df

    def summary_stats(self, emissions_df: gpd.GeoDataFrame, aoi: shapely.MultiPolygon) -> (pd.DataFrame, pd.DataFrame):
        """
        Calculate statistics about total change areas and emissions in the observation period.

        :param emissions_df: geodataframe with LULC change polygons and emissions [t] for each change type
        :param aoi: multipolygon of the area of interest
        :return: dataframe with statistics about emissions in the observation period
        :return: dataframe with statistics about change areas in the observation period
        """
        emissions_df = emissions_df.copy()
        subset_pos = emissions_df[emissions_df['emissions'] > 0]
        subset_neg = emissions_df[emissions_df['emissions'] < 0]
        emission_info = self.emission_summary(emissions_df, subset_pos, subset_neg)
        area_info = self.area_summary(emissions_df, subset_pos, subset_neg, aoi)
        return emission_info, area_info

    @staticmethod
    def emission_summary(
        emissions_df: gpd.GeoDataFrame, subset_pos: gpd.GeoDataFrame, subset_neg: gpd.GeoDataFrame
    ) -> pd.DataFrame:
        """
        Creates emission summary table.
        :param emissions_df: geodataframe with LULC change polygons and emissions [t] for each change type
        :param subset_pos: subset of emissions_df with LULC change polygons causing emissions
        :param subset_neg: subset of emissions_df with LULC change polygons causing sinks
        :return: dataframe with statistics about emissions in the observation period
        """
        total_gross_emissions = round(subset_pos['emissions'].sum(), 2)
        total_gross_sink = round(subset_neg['emissions'].sum(), 2)
        total_net_emissions = round(emissions_df['emissions'].sum(), 2)
        data_emission_info = [
            ['Gross Emissions', total_gross_emissions],
            ['Gross Sink', total_gross_sink],
            ['Net Emissions/Sink', total_net_emissions],
        ]
        emission_info = pd.DataFrame(data_emission_info, columns=['Metric Name', 'Value [t]'])
        emission_info.set_index('Metric Name', inplace=True)
        return emission_info

    @staticmethod
    def area_summary(
        emissions_df: gpd.GeoDataFrame,
        subset_pos: gpd.GeoDataFrame,
        subset_neg: gpd.GeoDataFrame,
        aoi: shapely.MultiPolygon,
    ) -> pd.DataFrame:
        """
        Creates change area summary table.
        :param emissions_df: geodataframe with LULC change polygons and emissions [t] for each change type
        :param subset_pos: subset of emissions_df with LULC change polygons causing emissions
        :param subset_neg: subset of emissions_df with LULC change polygons causing sinks
        :param aoi: multipolygon of the area of interest
        :return: dataframe with statistics about change areas in the observation period
        """
        total_emission_change_area = round(subset_pos.area.sum() * SQM_TO_HA, 2)
        total_sink_change_area = round(subset_neg.area.sum() * SQM_TO_HA, 2)

        wgs84 = pyproj.CRS('EPSG:4326')
        project = pyproj.Transformer.from_crs(wgs84, emissions_df.crs, always_xy=True).transform
        utm_aoi = transform(project, aoi)

        emitting_change_area_percent = round(subset_pos.area.sum() / utm_aoi.area * 100, 2)
        sink_change_area_percent = round(subset_neg.area.sum() / utm_aoi.area * 100, 2)

        aoi_area = round(utm_aoi.area * SQM_TO_HA, 2)
        relative_aoi_area = round(utm_aoi.area / utm_aoi.area * 100, 2)

        total_change_area = round(emissions_df.area.sum() * SQM_TO_HA, 2)
        relative_change_area = round(emissions_df.area.sum() / utm_aoi.area * 100, 2)
        data_area_info = [
            ['Area of Interest (AOI)', aoi_area, relative_aoi_area],
            ['Change Area', total_change_area, relative_change_area],
            ['Emitting Area', total_emission_change_area, emitting_change_area_percent],
            ['Sink Area', total_sink_change_area, sink_change_area_percent],
        ]
        area_info = pd.DataFrame(
            data_area_info, columns=['Metric Name', 'Absolute Value [ha]', 'Proportion of AOI [%]']
        )
        area_info.set_index('Metric Name', inplace=True)
        return area_info

    def get_change_type_table(self, emissions_df: gpd.GeoDataFrame) -> pd.DataFrame:
        """
        Creates a table showing total LULC change area [ha] and total LULC change emissions [t] per change type.

        :param emissions_df: geodataframe with LULC class names at time stamps 1 and 2 as well as LULC change polygons
        and emissions [t] per change type
        :return: dataframe with total LULC change area [ha] and total LULC change emissions [t] per change type
        """
        change_type_df = emissions_df.copy()

        change_type_df['Change'] = change_type_df.apply(
            lambda row: f'{row.utility_class_name_before} to {row.utility_class_name_after}', axis=1
        )
        change_type_df['Area [ha]'] = round(change_type_df.area * SQM_TO_HA, 2)
        change_type_df['Total emissions [t]'] = round(change_type_df.emissions, 2)

        change_type_df = change_type_df.set_index('Change')

        change_type_df = change_type_df.sort_values('Total emissions [t]')

        return change_type_df[['Area [ha]', 'Total emissions [t]']]

    def area_plot(self, emissions_df: gpd.GeoDataFrame) -> Chart2dData:
        """
        Creates pie chart showing change area by LULC change type as Chart2dData object and .png file.

        :param emissions_df: geodataframe with change area by LULC change type
        :return: Chart2dData object with change area by LULC change type
        """
        emissions_df = emissions_df.sort_values(by='emissions')

        areas = emissions_df.area * SQM_TO_HA
        labels = emissions_df.apply(
            lambda row: f'{row.utility_class_name_before} to {row.utility_class_name_after}', axis=1
        )
        colors = emissions_df.color

        area_chart_data = self.get_area_chart2ddata(areas, labels, colors)

        return area_chart_data

    def get_area_chart2ddata(self, sizes: pd.Series, labels: pd.Series, colors: pd.Series) -> Chart2dData:
        """
        :param sizes: pd.Series with change areas by LULC change type
        :param labels: pd.Series with LULC change type labels
        :param colors: pd.Series with plot color for each LULC change type
        :return: Chart2dData object for pie chart showing change areas by LULC change type
        """
        area_chart_data = Chart2dData(
            x=labels.to_list(), y=sizes.to_list(), color=colors.to_list(), chart_type=ChartType.PIE
        )
        return area_chart_data

    def emission_plot(self, emissions_df: gpd.GeoDataFrame) -> Chart2dData:
        """
        Creates horizontal bar chart showing carbon emissions by LULC change type as Chart2dData object and .png file.

        :param emissions_df: geodataframe with carbon emissions by LULC change type
        :return: Chart2dData object with carbon emissions by LULC change type
        :return: horizontal bar chart image with carbon emissions by LULC change type
        """
        emissions_df = emissions_df.sort_values(by='emissions')

        emissions = emissions_df['emissions']
        labels = emissions_df.apply(
            lambda row: f'{row.utility_class_name_before} to {row.utility_class_name_after}',
            axis=1,
        )

        emission_chart_data = self.get_emission_chart2ddata(emissions, labels)

        return emission_chart_data

    def get_emission_chart2ddata(self, emissions: pd.Series, labels: pd.Series) -> Chart2dData:
        """
        :param emissions: pd.Series with emissions by LULC change type
        :param labels: pd.Series with LULC change type labels
        :param colors: pd.Series with plot color for each LULC change type
        :return: Chart2dData object for bar chart showing emissions by LULC change type
        """
        emission_chart_data = Chart2dData(
            x=labels.to_list(),
            y=emissions.to_list(),
            color=emissions.size * [Color('gray')],
            chart_type=ChartType.BAR,
        )
        return emission_chart_data

    @staticmethod
    def filter_ghg_stock(ghg_stock: pd.DataFrame) -> pd.DataFrame:
        """
        Filters GHG stock dataframe and renames columns.

        :param ghg_stock: dataframe with original class names and definitions, utility class name, GHG stock,
        description, OSM filter, raster value, and color
        :return: dataframe with class name and description (from utility) and GHG stock value
        """
        ghg_stock = ghg_stock.copy()
        ghg_stock = ghg_stock.sort_values('ghg_stock')
        ghg_stock = ghg_stock[['utility_class_name', 'description', 'ghg_stock']]
        ghg_stock = ghg_stock.rename(
            columns={
                'utility_class_name': 'Class',
                'description': 'Definition',
                'ghg_stock': 'GHG stock value [t/ha]',
            }
        )
        ghg_stock.set_index('Class', inplace=True)
        return ghg_stock
