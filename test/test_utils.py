import numpy as np
import pandas as pd
import rasterio
from numpy import ma
from pydantic_extra_types.color import Color
from shapely import Polygon

from ghg_lulc.utils import GhgStockSource, calc_emission_factors, get_colors, get_ghg_stock, mask_raster


def test_get_ghg_stock(lulc_utility_mock):
    calculated_value = get_ghg_stock(lulc_utility_mock.get_class_legend())
    assert calculated_value.get(GhgStockSource.HANSIS).size == 8 * 4


def test_calc_emission_factors(lulc_utility_mock):
    calculated_emission_factors = calc_emission_factors(get_ghg_stock(lulc_utility_mock.get_class_legend()))
    assert calculated_emission_factors.get(GhgStockSource.HANSIS).size == 16 * 7
    assert calculated_emission_factors.get(GhgStockSource.HANSIS).emission_factor.sum() == 0
    assert 'color' in calculated_emission_factors.get(GhgStockSource.HANSIS).columns


def test_mask_raster():
    input_array = np.ones((1, 3, 3), dtype=np.uint8)
    input_geom = Polygon(
        [
            [8.5901, 49.43],
            [8.5904, 49.43],
            [8.5904, 49.44],
            [8.5901, 49.44],
            [8.5901, 49.43],
        ]
    )
    input_transform = rasterio.transform.Affine(0.00013748191027496346, 0.0, 8.59, 0.0, -9.049773755655916e-05, 49.44)

    expected_array = ma.masked_array(
        [[[1, 1, 1], [1, 1, 1], [1, 1, 1]]],
        mask=[
            [
                [1, 0, 0],
                [1, 0, 0],
                [1, 0, 0],
            ]
        ],
    )

    lulc_output = mask_raster(input_array, input_geom, input_transform)

    assert ma.allequal(lulc_output, expected_array)
    assert np.array_equal(lulc_output.mask, expected_array.mask)


def test_get_colors():
    emissions = pd.Series([-376.6, -19.12, 0, 16.8, 310.97])
    colors = pd.Series([Color('#00004c'), Color('#e5e5ff'), Color('#fffdfd'), Color('#ffe9e9'), Color('#ac0000')])
    color_col = get_colors(emissions)
    pd.testing.assert_series_equal(color_col, colors)
