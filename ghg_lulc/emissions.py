import logging
from pathlib import Path
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

from ghg_lulc.utils import SQM_TO_HA, STOCK_TARGET_AREA, pyplot_to_pydantic_color, PIXEL_AREA

log = logging.getLogger(__name__)


class EmissionCalculator:

    def __init__(self, emission_factors: pd.DataFrame, resources: ComputationResources):
        self.emission_factors = emission_factors
        self.resources = resources

    def derive_lulc_changes(self,
                            lulc_before: RasterInfo,
                            lulc_after: RasterInfo) -> Tuple[RasterInfo, RasterInfo]:
        """
        Check if there is a LULC change in each cell and what kind of LULC change. Then it assigns a specific integer
        for each LULC change type to the cell and returns a ndarray.

        :param lulc_before: LULC classification of first time stamp
        :param lulc_after: LULC classification of second time stamp
        :return: a raster with LULC changes and a raster with pixel wise emissions
        between first and second time stamp
        """
        log.debug('Deriving LULC changes')

        changes_info = self.get_change_info(lulc_before, lulc_after)

        change_emissions_info = self.get_change_emissions_info(changes_info)

        return changes_info, change_emissions_info

    def get_change_info(self, lulc_before: RasterInfo, lulc_after: RasterInfo,
                        unknown_change_value: int = -1, no_change_value: int = 0) -> RasterInfo:
        changes = np.full_like(lulc_before.data, fill_value=unknown_change_value, dtype=np.int16)

        for row in self.emission_factors.itertuples():
            changes[(lulc_before.data == row.raster_value_before) &
                    (lulc_after.data == row.raster_value_after)] = row.change_id

        changes[lulc_before.data == lulc_after.data] = no_change_value

        cmap = plt.get_cmap('tab20b')
        changes_colormap = {}

        change_classes = np.unique(ma.compressed(changes))
        for change_class in change_classes:
            pyplot_color = cmap(change_class / max(change_classes))
            changes_colormap[change_class] = pyplot_to_pydantic_color(pyplot_color).as_rgb_tuple()
        changes_colormap[no_change_value] = Color('gray').as_rgb_tuple()
        changes_colormap[unknown_change_value] = Color('black').as_rgb_tuple()

        return RasterInfo(data=changes,
                          crs=lulc_before.crs,
                          transformation=lulc_before.transformation,
                          colormap=changes_colormap,
                          nodata=unknown_change_value)

    def get_change_emissions_info(self, changes: RasterInfo, unknown_emissions_value: float = -999.999) -> RasterInfo:
        emission_per_pixel_factor = PIXEL_AREA / STOCK_TARGET_AREA

        change_emissions = np.full_like(changes.data, fill_value=unknown_emissions_value, dtype=np.floating)

        emissions_colormap = {}
        for row in self.emission_factors.itertuples():
            pixel_emissions = row.emission_factor * emission_per_pixel_factor

            change_emissions[changes.data == row.change_id] = pixel_emissions
            emissions_colormap[pixel_emissions] = row.color.as_rgb_tuple()
        change_emissions[changes.data == 0] = 0

        emissions_colormap[unknown_emissions_value] = Color('black').as_rgb_tuple()

        return RasterInfo(data=change_emissions,
                          crs=changes.crs,
                          transformation=changes.transformation,
                          colormap=emissions_colormap,
                          nodata=unknown_emissions_value)

    def convert_change_raster(self, change_raster: RasterInfo) -> gpd.GeoDataFrame:
        """
        Converts the LULC change raster to a geodataframe. Then, it reprojects the geodataframe to a projected
        coordinate system, so we can perform area-based calculations on it.

        :param change_raster: The LULC change raster data
        :return: geodataframe with LULC change polygons and emission factors
        """
        log.debug(f'Converting change raster of shape {change_raster.data.shape} with dtype '
                  f'{change_raster.data.dtype} to vector')

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

        calculate absolute LULC change emissions per polygon by multiplying emission factor with area
        :param change_df: geodataframe with LULC change polygons, their area and their emissions in t/ha
        :return: emission_factor_df with additional absolute emissions column
        """
        change_df = change_df.copy()
        change_df['emissions'] = change_df.area * SQM_TO_HA * change_df['emission_factor']

        return change_df

    @staticmethod
    def summary_stats(emissions_df: gpd.GeoDataFrame, aoi: shapely.MultiPolygon) -> pd.DataFrame:
        """
        Create summary data frame.
        """
        emissions_df = emissions_df.copy()
        subset_pos = emissions_df[emissions_df['emissions'] > 0]
        subset_neg = emissions_df[emissions_df['emissions'] < 0]

        total_gross_emissions = round(subset_pos['emissions'].sum(), 1)
        total_gross_sink = round(subset_neg['emissions'].sum(), 1)
        total_net_emissions = round(emissions_df['emissions'].sum(), 1)

        total_emission_change_area = round(subset_pos.area.sum() * SQM_TO_HA, 2)
        total_sink_change_area = round(subset_neg.area.sum() * SQM_TO_HA, 2)

        emitting_change_area_percent = round(subset_pos.area.sum() / emissions_df.area.sum() * 100, 1)
        sink_change_area_percent = round(subset_neg.area.sum() / emissions_df.area.sum() * 100, 1)

        wgs84 = pyproj.CRS('EPSG:4326')
        project = pyproj.Transformer.from_crs(wgs84, emissions_df.crs, always_xy=True).transform
        utm_aoi = transform(project, aoi)
        aoi_area = round(utm_aoi.area * SQM_TO_HA, 1)

        relative_change_area = round(emissions_df.area.sum() / utm_aoi.area * 100, 2)

        data = [['Area of interest [ha]', aoi_area],
                ['Change share [%]', relative_change_area],
                ['Emitting area [ha]', total_emission_change_area],
                ['Emitting area share [%]', emitting_change_area_percent],
                ['Sink area [ha]', total_sink_change_area],
                ['Sink area share [%]', sink_change_area_percent],
                ['Total gross emissions [t]', total_gross_emissions],
                ['Total sink [t]', total_gross_sink],
                ['Net emissions [t]', total_net_emissions]]

        summary = pd.DataFrame(data, columns=['Metric name', 'Value'])
        summary.set_index('Metric name', inplace=True)

        return summary

    def get_change_type_table(self, emissions_df: gpd.GeoDataFrame) -> pd.DataFrame:
        change_type_df = emissions_df.copy()

        change_type_df['Change'] = change_type_df.apply(
            lambda row: f'{row.utility_class_name_before} to {row.utility_class_name_after}',
            axis=1)
        change_type_df['Area [ha]'] = round(change_type_df.area * SQM_TO_HA, 2)
        change_type_df['Total emissions [t]'] = round(change_type_df.emissions, 2)

        change_type_df = change_type_df.set_index('Change')

        change_type_df = change_type_df.sort_values('Total emissions [t]')

        return change_type_df[['Area [ha]', 'Total emissions [t]']]

    def area_plot(self, emissions_df: gpd.GeoDataFrame) -> Tuple[Chart2dData, Path]:
        """

        :param emissions_df: dataframe with stats per change type
        :return: Chart2dData object with change area by LULC change type
        :return: pie chart image with change area by LULC change type
        """
        emissions_df = emissions_df.sort_values(by='emissions')

        areas = emissions_df.area * SQM_TO_HA
        labels = emissions_df.apply(
            lambda row: f'{row.utility_class_name_before} to {row.utility_class_name_after}',
            axis=1)
        colors = emissions_df.color

        area_chart_data = self.get_area_chart2ddata(areas, labels, colors)

        area_chart_file = self.get_area_pyplot(areas, labels, colors)

        return area_chart_data, area_chart_file

    def get_area_chart2ddata(self, sizes: pd.Series, labels: pd.Series, colors: pd.Series) -> Chart2dData:
        area_chart_data = Chart2dData(x=labels.to_list(),
                                      y=sizes.to_list(),
                                      color=colors.to_list(),
                                      chart_type=ChartType.PIE)
        return area_chart_data

    def get_area_pyplot(self, sizes: pd.Series, labels: pd.Series, colors: pd.Series) -> Path:
        fig, ax = plt.subplots()
        ax.pie(sizes,
               labels=labels,
               colors=colors.apply(lambda val: val.as_hex()).to_list())
        areas_chart_file = self.resources.computation_dir / 'areas.png'
        plt.title('Change area by LULC change type [ha]')
        plt.savefig(areas_chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        return areas_chart_file

    def emission_plot(self, emissions_df: gpd.GeoDataFrame) -> Tuple[Chart2dData, Path]:
        """

        :param emissions_df: dataframe with stats per change type
        :return: Chart2dData object with carbon emissions by LULC change type
        :return: horizontal bar chart image with carbon emissions by LULC change type
        """
        emissions_df = emissions_df.sort_values(by='emissions')

        emissions = emissions_df['emissions']
        labels = emissions_df.apply(
            lambda row: f'{row.utility_class_name_before} to {row.utility_class_name_after}',
            axis=1)
        colors = emissions_df['color']

        emission_chart_data = self.get_emission_chart2ddata(emissions, labels, colors)

        emission_chart_file = self.get_emission_pyplot(emissions, labels, colors)

        return emission_chart_data, emission_chart_file

    def get_emission_chart2ddata(self, emissions: pd.Series, labels: pd.Series, colors: pd.Series) -> Chart2dData:
        emission_chart_data = Chart2dData(x=labels.to_list(),
                                          y=emissions.to_list(),
                                          color=colors.to_list(),
                                          chart_type=ChartType.BAR)
        return emission_chart_data

    def get_emission_pyplot(self, emissions: pd.Series, labels: pd.Series, colors: pd.Series) -> Path:
        fig, (ax) = plt.subplots(figsize=(8, 4))

        bars = ax.barh(width=emissions, y=labels, color=colors.apply(lambda val: val.as_hex()).to_list())

        ax.bar_label(bars, padding=2, fmt='%.2f')
        ax.set_xlabel('carbon emissions [t]')
        ax.set_title('Carbon emissions by LULC change type [t]')

        # we add a small padding to the chart to prevent bar labels from overlapping the axis
        x_min = min(emissions.min() + emissions.min() / 3, 0)
        x_max = max(emissions.max() + emissions.max() / 3, 0)
        ax.set_xlim(x_min, x_max)

        fig.tight_layout()
        emission_chart_file = self.resources.computation_dir / 'emissions.png'
        plt.savefig(emission_chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        return emission_chart_file

    @staticmethod
    def filter_ghg_stock(ghg_stock: pd.DataFrame) -> pd.DataFrame:
        ghg_stock = ghg_stock.copy()
        ghg_stock = ghg_stock.sort_values('ghg_stock')
        ghg_stock = ghg_stock[['utility_class_name', 'description', 'ghg_stock']]
        ghg_stock = ghg_stock.rename(columns={'utility_class_name': 'Class',
                                              'description': 'Definition',
                                              'ghg_stock': 'GHG stock value [t/ha]'})
        ghg_stock.set_index('Class', inplace=True)
        return ghg_stock
