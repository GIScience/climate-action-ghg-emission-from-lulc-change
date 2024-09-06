import logging
from enum import Enum
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import shapely
from affine import Affine
from climatoology.base.artifact import RasterInfo
from climatoology.utility.api import LabelDescriptor, LulcUtility, LulcWorkUnit
from matplotlib import pyplot as plt
from matplotlib.colors import TwoSlopeNorm, to_hex
from pydantic_extra_types.color import Color
from rasterio.features import geometry_mask

log = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent

PIXEL_AREA = 10 * 10
STOCK_TARGET_AREA = 100 * 100
SQM_TO_HA = 1 / STOCK_TARGET_AREA

EMISSION_PER_PIXEL_FACTOR = PIXEL_AREA / STOCK_TARGET_AREA

RASTER_NO_DATA_VALUE = np.iinfo(np.uint8).max

UNKNOWN_CLASS_LABEL = LabelDescriptor(
    name='unknown',
    description='The class is unknown',
    osm_filter=None,
    raster_value=0,
    color=(0, 0, 0),
)


class GhgStockSource(Enum):
    HANSIS = 'Hansis et al. (2015): Carbon stock values from the BLUE model.'
    HANSIS_HIGHER = 'Hansis et al. (2015) - Higher: Higher carbon stock values based Reick et al. (2010).'
    HOUGHTON = 'Houghton & Hackler (2001): Carbon stock values from a database of the Carbon Dioxide Information '
    'Analysis Center.'


def get_ghg_stock(utility_labels: Dict[str, LabelDescriptor]) -> Dict[GhgStockSource, pd.DataFrame]:
    """
    Get GHG stocks from each GHG stock source.

    :param utility_labels: Dict containing the LULC labels from the LULC utility and their label descriptors
    :return: Dict containing a DataFrame of each GHG stock source with information about the LULC classes such as class
    name, class description, and GHG stock
    """
    ghg_stock = {}
    source_base_path = Path('resources/ghg_stock_sources')
    for source in GhgStockSource:
        ghg_stock[source] = read_stock_source(source_base_path / f'{source.name.lower()}.csv', utility_labels)

    return ghg_stock


def read_stock_source(source_file: Path, utility_labels: Dict[str, LabelDescriptor]) -> pd.DataFrame:
    """
    Get GHG stocks from the source file.

    :param source_file: Path of the GHG stock source file
    :param utility_labels: Dict containing the LULC labels from the LULC utility and their label descriptors
    :return: DataFrame with information about the LULC classes such as class name, class description, and GHG stock
    """
    ghg_stock = pd.read_csv(source_file)
    try:
        utility_label_descriptors = ghg_stock.apply(
            lambda row: utility_labels.get(row.utility_class_name, UNKNOWN_CLASS_LABEL).model_dump(
                exclude={'name', 'osm_ref'}
            ),
            axis='columns',
            result_type='expand',
        )
    except AttributeError as e:
        log.error(
            'One of the expected utility class names defined in the ghg stock source is unknown to the lulc '
            'utility.',
            exc_info=e,
        )
        raise e
    return pd.concat([ghg_stock, utility_label_descriptors], axis='columns')


def calc_emission_factors(ghg_stock: Dict[GhgStockSource, pd.DataFrame]) -> Dict[GhgStockSource, pd.DataFrame]:
    """
    Derive emission factors [t/ha] for each GHG stock source.

    :param ghg_stock: Dict containing a DataFrame of each GHG stock source with information about the LULC classes
    such as class name, class description, and GHG stock
    :return: Dict containing a DataFrame of each GHG stock source with emission factor [t/ha] for each LULC change type
    """
    emission_factors = {}
    for source, stock in ghg_stock.items():
        emission_factor = stock.merge(stock, how='cross', suffixes=('_before', '_after'))
        emission_factor['change_id'] = pd.RangeIndex(start=1, stop=len(emission_factor) + 1)
        emission_factor['emission_factor'] = emission_factor['ghg_stock_before'] - emission_factor['ghg_stock_after']
        emission_factor['color'] = get_colors(emission_factor['emission_factor'])
        emission_factors[source] = emission_factor[
            [
                'change_id',
                'utility_class_name_before',
                'raster_value_before',
                'utility_class_name_after',
                'raster_value_after',
                'emission_factor',
                'color',
            ]
        ]
    return emission_factors


def fetch_lulc(lulc_utility: LulcUtility, lulc_area: LulcWorkUnit, aoi: shapely.MultiPolygon) -> RasterInfo:
    """
    Get LULC classification for a certain timestamp.

    :param lulc_utility: A wrapper class around the LULC Utility API
    :param lulc_area: LulcWorkUnit containing AOI coordinates, dates of first and second timestamp, fusion mode, and
    LULC classification accuracy threshold
    :param aoi: Multipolygon of the AOI
    :return: RasterInfo object containing an array of the LULC in the AOI and the meta information needed to create
    the LULC raster
    """
    log.debug('Fetching classification.')
    with lulc_utility.compute_raster([lulc_area]) as lulc_classification:
        lulc_array = lulc_classification.read().astype(np.uint8)
        crs = lulc_classification.crs
        transform = lulc_classification.transform
        colormap = lulc_classification.colormap(1)

    masked_lulc = mask_raster(lulc_array, aoi, transform)

    return RasterInfo(
        data=masked_lulc,
        crs=crs,
        transformation=transform,
        colormap=colormap,
    )


def mask_raster(
    lulc_array: np.array,
    aoi: shapely.MultiPolygon,
    transform: Affine,
) -> np.array:
    """
    Mask LULC raster to the AOI.

    :param lulc_array: Array with the LULC values for bounding box of the AOI, as returned by the LULCUtility
    :param aoi: Multipolygon of the AOI
    :param transform: Information needed to transform coordinates from image pixel (row, col) to and from
    geographic/projected (x, y) coordinates
    :return: Array of the LULC in the AOI
    """
    rows = lulc_array.shape[-2]
    cols = lulc_array.shape[-1]
    mask = ~geometry_mask([aoi], (rows, cols), transform=transform, invert=True)
    masked_lulc_array = np.ma.masked_array(lulc_array, mask, fill_value=RASTER_NO_DATA_VALUE)

    return masked_lulc_array


def get_colors(values: pd.Series) -> pd.Series:
    """
    Convert a Series of numeric values to colors taken from a scaled bi-directional colormap with center point 0.

    :param values: Values to convert to colors
    :return: Column of colors
    """
    cmap = plt.get_cmap('seismic')
    min_val = values.min()
    max_val = values.max()
    abs_max_val = max(abs(min_val), abs(max_val))
    norm = TwoSlopeNorm(vmin=-abs_max_val, vcenter=0, vmax=abs_max_val)
    color_col = values.apply(lambda x: pyplot_to_pydantic_color(cmap(norm(x))))

    return color_col


def pyplot_to_pydantic_color(pyplot_tuple: np.ndarray) -> Color:
    return Color(to_hex(pyplot_tuple))
