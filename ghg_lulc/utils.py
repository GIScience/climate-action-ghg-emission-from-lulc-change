import geopandas as gpd


def convert_to_gdf(dataset):
    # Convert rioxarray to pandas DataFrame
    dataframe = dataset.to_dataframe()

    # Convert pandas DataFrame to GeoPandas DataFrame
    geodataframe = gpd.GeoDataFrame(dataframe)

    # Set the geometry column of the GeoPandas DataFrame
    geodataframe.geometry = geodataframe.index.to_series().apply(
        dataset.rio.transform * dataset.rio.height_of_upper_left_pixel / 2 + dataset.rio.transform * dataset.rio.res[
            0] / 2)
    return geodataframe


def apply_conditions(row):
    if row['emissions_per_ha'] == -156.0:
        return 'settlement to forest'
    elif row['emissions_per_ha'] == -121.0:
        return 'farmland to forest'
    elif row['emissions_per_ha'] == -119.5:
        return 'meadow to forest'
    elif row['emissions_per_ha'] == -36.5:
        return 'settlement to meadow'
    elif row['emissions_per_ha'] == -35.0:
        return 'settlement to farmland'
    elif row['emissions_per_ha'] == -1.5:
        return 'farmland to meadow'
    elif row['emissions_per_ha'] == 0.0:
        return 'no LULC change'
    elif row['emissions_per_ha'] == 1.5:
        return 'meadow to farmland'
    elif row['emissions_per_ha'] == 35.0:
        return 'farmland to settlement'
    elif row['emissions_per_ha'] == 36.5:
        return 'meadow to settlement'
    elif row['emissions_per_ha'] == 119.5:
        return 'forest to meadow'
    elif row['emissions_per_ha'] == 121.0:
        return 'forest to farmland'
    elif row['emissions_per_ha'] == 156.0:
        return 'forest to settlement'
    else:
        return ''
