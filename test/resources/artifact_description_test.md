# Description of the artifacts

- **Period start:** 2022-05-17

- **Period end:** 2023-05-31

- **Minimum required classification confidence [%]:** 75.0

## Map: LULC classifications

A LULC classification is provided for the start date and the end date of the observation period.
The classes included are given in Table 1.
The model’s confidence for all areas that have been assigned a LULC class lies above the selected classification confidence threshold.
All areas where the model’s confidence lies below the threshold have been classified as “unknown”.

The LULC classifications are made by a machine learning model using satellite images.
Since clouds may obstruct the area or parts of it in a single image, the LULC classification model uses an entire week of satellite images before the selected date to derive the classification.
Aside from cloud cover, the LULC classification is subject to multiple inaccuracies which can potentially create random change pixels for unchanged regions, such as the salt-and-pepper effect[^1], atmospheric influences[^2], mixed pixels[^3] etc.

[^1]: The salt-and-pepper effect occurs often in pixel-based image classifications.
If the images are noisy or there are only few, very general classes, like in this case, it can happen that adjacent pixels are seemingly randomly assigned to different classes so that it looks as if salt and pepper were sprinkled over the image.

[^2]: Atmospheric influences such as scattering and absorption of sunlight by atmospheric molecules and aerosols that cause haziness in the image can change the image color in one of the points-in-time, even if there was no LULC change.

[^3]: Mixed pixels occur if the land cover varies within the pixel.
The pixel size of our data is 10 m, so this occurs often, especially at the borders of different LULC classes.
At the edge between two LULC classes, a pixel might be assigned to class _A_ at the first point-in-time and to class _B_ at the second point-in-time, because of course it can only be assigned to one class.

## Map: LULC change

The LULC changes that occurred during the observation period are shown in this map.

## Map: Localized emissions - GHG emissions per pixel due to LULC change (t)

The LULC change emissions per pixel (t) during the observation period are shown in this map.
Emissions are estimated in the following way: To each LULC, specific carbon stocks are assigned, e.g. a forest stores more carbon than a meadow or a settlement.
The carbon stocks of the selected source are shown in Table 1.
These carbon stocks encompass soil and vegetation carbon, providing an average measure of carbon stored per hectare.
Our method compares LULC and its associated carbon stock at time stamp 1 with LULC and its associated carbon stock at time stamp 2, i. e. we subtract the associated carbon stock of time stamp 2 from the carbon stock of time stamp 1.
The resulting emission factors are shown in Table 2.
Positive emission values indicate carbon emissions, negative emission values indicate a carbon sink resulting from the LULC change.

It is assumed that each location experiences maximally one LULC change during the observation period.
Emission factors are only available for the LULC change types given in Table 2.
All other LULC change types are in the unknown class.
The emission factors only account for emissions caused by vegetation removal (e.g. clearing of forest for urban development).
They do not include subsequent emissions caused by e.g. construction of buildings.
With respect to this, real emissions will thus be higher.

**Table 1. Carbon stocks of the LULC classes in t/ha**

| LULC Class   |   Carbon stock [t/ha] |
|:-------------|----------------------:|
| forest       |                 253.0 |
| grass        |                 161.5 |
| farmland     |                 108.0 |
| built-up     |                  71.0 |

The carbon stock value for settlement is a combination of the soil carbon value 60 t/ha (Bradley et al., 2006) and vegetation carbon value 11 t/ha (Strohbach & Haase, 2012).

**Table 2. Carbon emissions of the LULC change types in t/ha**

| From Class   | To Class   |   Factor [t/ha] |
|:-------------|:-----------|----------------:|
| forest       | forest     |             0.0 |
| forest       | grass      |            91.5 |
| forest       | farmland   |           145.0 |
| forest       | built-up   |           182.0 |
| grass        | forest     |           -91.5 |
| grass        | grass      |             0.0 |
| grass        | farmland   |            53.5 |
| grass        | built-up   |            90.5 |
| farmland     | forest     |          -145.0 |
| farmland     | grass      |           -53.5 |
| farmland     | farmland   |             0.0 |
| farmland     | built-up   |            37.0 |
| built-up     | forest     |          -182.0 |
| built-up     | grass      |           -90.5 |
| built-up     | farmland   |           -37.0 |
| built-up     | built-up   |             0.0 |

## Bar chart: Carbon emissions by LULC change type [t]

This bar chart shows the total carbon emissions by LULC change type [t] in the observation period.

## Pie Chart: Change areas by LULC change type [ha]

This pie chart shows the total change areas by LULC change type [% of total change area] in the observation period.
The total change area is the total area of all LULC changes for which an emission factor is available.
The slices of the bar chart are colored according to the emissions per pixel of the respective LULC change type.
Since it has the highest carbon emissions per pixel, the LULC change type "forest to built-up" is colored in the darkest red.
Accordingly, the LULC change type "built-up to forest" is colored in the darkest blue, because it has the highest carbon sink per pixel.

## Table: Carbon stock values per class

The table contains the class definition and the carbon stock value for each class according to the selected GHG stock source.
For the emission estimation, you can choose between three different sets of carbon stock values: (1) Carbon stock values from the BLUE model (Hansis et al., 2015), (2) higher carbon stock values from Hansis et al. (2015) based on Reick et al. (2010), and (3) carbon stock values from a database of the Carbon Dioxide Information Analysis Center (Houghton & Hackler, 2001).

## Table: Change areas and emissions by LULC change type

This table shows the total change area by LULC change type [ha] and the total change emissions by LULC change type [t] in the observation period.

## Table: Summary of results

This table shows the gross emissions, gross sinks, and net emissions/sinks in the observation period.
The term gross emissions refers to the total LULC change emissions of carbon to the atmosphere, the term gross sink refers to the total carbon sequestration as a result of LULC change, and the term net emissions/sink refers to the difference of carbon emissions and carbon sinks.

## Table: Information on the area of interest

This table shows the absolute size and the relative proportion with respect to the area of interest of the change area, emitting area, and sink area in the observation period.

## References

Bradley, R. i., Milne, R., Bell, J., Lilly, A., Jordan, C., & Higgins, A. (2005). A soil carbon and land use database for the United Kingdom. Soil Use and Management, 21(4), 363–369. [https://doi.org/10.1079/SUM2005351](https://doi.org/10.1079/SUM2005351)

Hansis, E., Davis, S. J., & Pongratz, J. (2015). Relevance of methodological choices for accounting of land use change carbon fluxes. Global Biogeochemical Cycles, 29(8), 1230–1246. [https://doi.org/10.1002/2014GB004997](https://doi.org/10.1002/2014GB004997)

Houghton, R. A., Hackler, J. L., & Cushman, R. M. (2001). Carbon flux to the atmosphere from land-use changes: 1850 to 1990. Oak Ridge: Carbon Dioxide Information Center, Environmental Sciences Division, Oak Ridge National Laboratory.

Strohbach, M. W., & Haase, D. (2012). Above-ground carbon storage by urban trees in Leipzig, Germany: Analysis of patterns in a European city. Landscape and Urban Planning, 104(1), 95–104. [https://doi.org/10.1016/j.landurbplan.2011.10.001](https://doi.org/10.1016/j.landurbplan.2011.10.001)