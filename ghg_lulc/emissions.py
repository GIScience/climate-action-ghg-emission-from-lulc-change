import logging
from pathlib import Path
from typing import Tuple, List

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from climatoology.base.artifact import Chart2dData, ChartType
from rasterio.features import shapes
from matplotlib.colors import TwoSlopeNorm, to_hex
from pydantic_extra_types.color import Color

from ghg_lulc.utils import apply_conditions

log = logging.getLogger(__name__)


class EmissionCalculator:

    def __init__(self, compute_dir: Path):
        self.compute_dir = compute_dir

    @staticmethod
    def derive_lulc_changes(lulc_array1: np.ndarray, lulc_array2: np.ndarray) -> Tuple[np.ndarray, dict]:
        """

        Check if there is a LULC change in each cell and what kind of LULC change. Then it assigns a specific integer
        for each LULC change type to the cell and returns a ndarray. Changes to or from water get the value 0 because
        we cannot calculate emissions for them.

         Cell value and corresponding LULC change type:
        0   default value or change from or to water
        1   settlement remaining settlement
        2   forest remaining forest
        3   water remaining water
        4   farmland remaining farmland
        5   meadow remaining meadow
        6   meadow to farmland
        7   farmland to settlement
        8   meadow to settlement
        9   forest to meadow
        10  forest to farmland
        11  forest to settlement
        12  settlement to forest
        13  farmland to forest
        14  meadow to forest
        15  settlement to meadow
        16  settlement to farmland
        17  farmland to meadow

        :param lulc_array1: LULC classification of first time period
        :param lulc_array2: LULC classification of second time period
        :return: ndarray with LULC changes between first and second time period
        """

        log.info('deriving LULC changes')

        reclassification = [(1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5), (1, 2, 12), (1, 4, 16), (1, 5, 15),
                            (2, 1, 11), (2, 4, 10), (2, 5, 9), (4, 1, 7), (4, 2, 13), (4, 5, 17), (5, 1, 8),
                            (5, 2, 14), (5, 4, 6)]

        changes = np.zeros_like(lulc_array1)

        for a1, a2, target in reclassification:
            changes[(lulc_array1 == a1) & (lulc_array2 == a2)] = target

        change_colormap = {
            0: (0, 0, 0, 255),
            1: (190, 190, 190, 255),
            2: (190, 190, 190, 255),
            3: (190, 190, 190, 255),
            4: (190, 190, 190, 255),
            5: (190, 190, 190, 255),
            6: (255, 102, 102, 255),
            7: (255, 51, 51, 255),
            8: (255, 0, 0, 255),
            9: (204, 0, 0, 255),
            10: (153, 0, 0, 255),
            11: (102, 0, 0, 255),
            12: (0, 0, 153, 255),
            13: (0, 0, 204, 255),
            14: (0, 0, 255, 255),
            15: (51, 51, 255, 255),
            16: (0, 128, 255, 255),
            17: (102, 178, 255, 255)}

        return changes, change_colormap

    def export_raster(self, changes: np.ndarray, meta: dict):
        """

        :param changes: ndarray with LULC changes between first and second time period
        :param meta: parameters for generation of geotiff
        """
        change_file = self.compute_dir / 'LULC_change.tif'

        with rasterio.open(change_file, 'w', **meta) as dst:
            dst.write(changes, 1)

    def convert_raster(self) -> gpd.GeoDataFrame:
        """

        Converts the LULC change raster to a geodataframe. Then, it reprojects the geodataframe to the projected
        coordinate system (EPSG:25832), so we can perform area-based calculations on it. For study areas outside UTM
        zone 32N, the coordinate system must be adapted!

        :return: geodataframe with LULC change polygons
        """

        with rasterio.open(self.compute_dir / 'LULC_change.tif') as src:
            image = src.read(1).astype(np.int16)
            crs = src.crs

            log.info('converting raster to vector')
            results = (
                {'properties': {'change_id': v}, 'geometry': s}
                for i, (s, v) in enumerate(shapes(image, mask=None, transform=src.transform))
            )

            org_df = gpd.GeoDataFrame.from_features(results, crs=crs)

        log.info('reprojecting geodataframe from %s to EPSG:25832' % crs)
        emission_factor_df = org_df.to_crs('EPSG:25832')

        return emission_factor_df

    @staticmethod
    def allocate_emissions(emission_factor_df: gpd.GeoDataFrame, emission_factors: list) -> gpd.GeoDataFrame:
        """

        The LULC change emissions [t/ha] are allocated to the LULC change polygons depending on the LULC change type.

        Carbon emissions in t/ha and corresponding LULC change type:
        -156    settlement to forest
        -121    farmland to forest
        -119.5  meadow to forest
        -36.5   settlement to meadow
        -35     settlement to farmland
        -1.5    farmland to meadow
        0       no change
        1.5     meadow to farmland
        35      farmland to settlement
        36.5    meadow to settlement
        119.5   forest to meadow
        121     forest to farmland
        156     forest to settlement

        :param emission_factor_df: geodataframe with LULC change polygons
        :param emission_factors: change_id and corresponding emission factor
        :return: geodataframe with LULC change polygons and their emissions in t/ha
        """
        log.info('allocating emission factors to the LULC change types')

        for i, v in emission_factors:
            emission_factor_df.loc[emission_factor_df['change_id'] == i, 'emissions per ha'] = v

        return emission_factor_df

    @staticmethod
    def calculate_total_change_area(emission_factor_df: gpd.GeoDataFrame) -> float:
        """

        calculate total LULC change area (ha) by summing up areas of polygons where emission factor != 0

        :param emission_factor_df: geodataframe with LULC change polygons and their emissions in t/ha
        :return: total LULC change area [ha]
        """
        subset = emission_factor_df[emission_factor_df['emissions per ha'] != 0]
        log.info('dividing area by 10000 to convert from m2 to ha')
        total_area = round(subset['geometry'].area.sum() / 10000, 2)

        return total_area

    @staticmethod
    def calculate_area_by_change_type(emission_factor_df: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
        """

        :param emission_factor_df: geodataframe with LULC change polygons and their emissions in t/ha
        :return: emission_factor_df with additional area column
        :return: dataframe with total change area by LULC change type
        """

        log.info('dividing area by 10000 to convert from m2 to ha')
        emission_factor_df['area'] = round(emission_factor_df['geometry'].area / 10000, 2)
        area_df = emission_factor_df.groupby('emissions per ha')['area'].sum().reset_index()
        area_df.rename(columns={'area': 'LULC change type area'}, inplace=True)

        return emission_factor_df, area_df

    @staticmethod
    def calculate_absolute_emissions_per_poly(emission_factor_df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """

        calculate absolute LULC change emissions per polygon by multiplying emission factor with area
        :param emission_factor_df: geodataframe with LULC change polygons, their area and their emissions in t/ha
        :return: emission_factor_df with additional absolute emissions column
        """
        emission_factor_df['emissions'] = emission_factor_df['area'] * emission_factor_df['emissions per ha']

        return emission_factor_df

    @staticmethod
    def add_colormap(emissions_col: pd.Series) -> pd.Series:
        """

        :param emissions_col: emission column that we want to display
        :return: additional color column that can be used for the color map
        """
        cmap = plt.get_cmap('seismic')
        min_val = emissions_col.min()
        max_val = emissions_col.max()
        abs_max_val = max(abs(min_val), abs(max_val))
        norm = TwoSlopeNorm(vmin=-abs_max_val, vcenter=0, vmax=abs_max_val)
        color_col = emissions_col.apply(lambda x: Color(to_hex(cmap(norm(x)))))

        return color_col

    @staticmethod
    def calculate_total_emissions(emission_factor_df: gpd.GeoDataFrame) -> Tuple[float, float, float]:
        """

        calculate total LULC change net carbon emissions, total gross emissions, and total sink
        :param emission_factor_df: geodataframe with LULC change polygons
        :return: total_net_emissions (net difference between emissions and sinks)
        :return: total_gross_emissions (only emissions)
        :return: total_sink (only sink)
        """
        subset_pos = emission_factor_df[emission_factor_df['emissions'] > 0]
        subset_neg = emission_factor_df[emission_factor_df['emissions'] < 0]

        total_net_emissions = round(emission_factor_df['emissions'].sum(), 1)
        total_gross_emissions = round(subset_pos['emissions'].sum(), 1)
        total_sink = round(subset_neg['emissions'].sum(), 1)

        return total_net_emissions, total_gross_emissions, total_sink

    @staticmethod
    def calculate_emissions_by_change_type(emission_factor_df: gpd.GeoDataFrame) -> pd.DataFrame:
        """

        calculate LULC change emissions by LULC change type by grouping the polygons by their emission factor and then
        summing up the absolute emissions for each group
        :param emission_factor_df: geodataframe with LULC change polygons
        :return: dataframe with the total LULC change emissions by change type
        """

        emission_sum_df = emission_factor_df.groupby('emissions per ha')['emissions'].sum().reset_index()
        emission_sum_df.rename(columns={'emissions': 'LULC change type emissions'}, inplace=True)

        return emission_sum_df

    @staticmethod
    def change_type_stats(area_df: pd.DataFrame, emission_sum_df: pd.DataFrame) -> pd.DataFrame:
        """

        :param area_df: dataframe with total change area by LULC change type
        :param emission_sum_df: dataframe with the total LULC change emissions by change type
        :return: out_df (dataframe with stats per change type)
        """
        out_df = area_df.merge(emission_sum_df, on='emissions per ha')
        out_df['LULC change type'] = out_df.apply(apply_conditions, axis=1)

        return out_df

    @staticmethod
    def summary_stats(total_area: float, total_net_emissions: float, total_gross_emissions: float,
                      total_sink: float) -> pd.DataFrame:
        """

        Exports dataframe with summary stats to csv
        :param total_area: total LULC change area [ha]
        :param total_net_emissions: net difference between total emissions and sinks
        :param total_gross_emissions: total emissions from all LULC changes
        :param total_sink: total sink from all LULC changes
        """

        data = {'metric name': ['total change area [ha]', 'total net emissions [t]', 'total gross emissions [t]',
                                'total sink [t]'],
                'value': [total_area, total_net_emissions, total_gross_emissions, total_sink]}
        summary = pd.DataFrame(data)
        summary.set_index('metric name', inplace=True)

        return summary

    def area_plot(self, out_df: pd.DataFrame, plot_colors: List[str]) -> Tuple[Chart2dData, Path]:
        """

        :param out_df: dataframe with stats per change type
        :param plot_colors: list with colors for the different change types
        :return: Chart2dData object with change area by LULC change type
        :return: pie chart image with change area by LULC change type
        """
        condition = out_df['LULC change type'] == 'no LULC change'
        out_df = out_df.loc[~condition]
        labels = out_df['LULC change type']
        sizes = out_df['LULC change type area']
        fig, ax = plt.subplots()
        ax.pie(sizes,
               labels=labels,
               colors=plot_colors)

        areas_chart_file = self.compute_dir / 'areas.png'

        plt.title('Change area by LULC change type [ha]')
        plt.savefig(areas_chart_file, dpi=300, bbox_inches='tight')
        plt.clf()

        area_chart_data = Chart2dData(x=labels.to_list(),
                                      y=sizes,
                                      color=[Color(color) for color in plot_colors],
                                      chart_type=ChartType.PIE)

        return area_chart_data, areas_chart_file

    def emission_plot(self, out_df: pd.DataFrame, plot_colors: List[str]) -> Tuple[Chart2dData, Path]:
        """

        :param out_df: dataframe with stats per change type
        :param plot_colors: list with colors for the different change types
        :return: Chart2dData object with carbon emissions by LULC change type
        :return: horizontal bar chart image with carbon emissions by LULC change type
        """
        condition = out_df['LULC change type'] == 'no LULC change'
        out_df = out_df.loc[~condition]
        categories = out_df['LULC change type']
        values = round(out_df['LULC change type emissions'], 0)
        y_pos = [0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75]

        fig, (ax) = plt.subplots(figsize=(8, 4))
        bars = ax.barh(y_pos, values, height=0.2, color=plot_colors)
        ax.bar_label(bars, padding=2)

        ax.set_xlabel('carbon emissions [t]')
        ax.set_title('Carbon emissions by LULC change type [t]')
        ax.set_yticks(y_pos, categories)

        x_min = values.min() + values.min() / 3
        x_max = values.max() + values.max() / 3

        ax.set_xlim(x_min, x_max)

        fig.tight_layout()

        emission_chart_file = self.compute_dir / 'emissions.png'
        plt.savefig(emission_chart_file, dpi=300, bbox_inches='tight')
        plt.clf()

        emission_chart_data = Chart2dData(x=y_pos,
                                          y=values.to_list(),
                                          color=[Color(color) for color in plot_colors],
                                          chart_type=ChartType.BAR)

        return emission_chart_data, emission_chart_file
