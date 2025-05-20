The methodology of the LULC Change Tool involves two main steps:

1. **Identifying Land Use and Land Cover (LULC) changes**

2. **Calculating carbon flows**

### Identifying Land Use and Land Cover (LULC) changes

By comparing the LULC classifications at the beginning and end of the period we can identify pixels that change from one class to another.
Computations are possible for time periods from 2017 onwards.
To obtain the LULC classifications, images from July of the respective year are used.
If the selected analysis period is e.g. 2017 to 2024, LULC changes from July 2017 until July 2024 will be computed.

The LULC classification has inherent uncertainties.
For example, it is influenced by clouds, which may obstruct the area or parts of it in a single image.
Aside from cloud cover, the LULC classification is subject to multiple inaccuracies which can potentially create random change pixels for unchanged regions, such as the salt-and-pepper effect, atmospheric influences, and mixed pixels.
Thus, a minimum classification confidence of 75 % is defined in the tool.
Any prediction where the model's confidence lies above this threshold will be assumed to be "true", all classification exhibiting lower confidence will be classified as "unknown".
Since the LULC classification model has been trained specifically for areas in Germany, the tool is currently limited to Germany.

### Calculating carbon flows

Carbon flows are calculated based on carbon stock differences between initial and final LULC classes.
The carbon stocks encompass soil and vegetation carbon, providing an average measure of carbon stored per hectare.
Various LULC change types are included and associated carbon emissions and sinks/sequestration (in tonnes/ha) are calculated.
To each LULC, specific carbon stocks are assigned, e.g. a forest stores more carbon than a meadow or built-up area (Table 1).
Our method thus compares LULC and its associated carbon stock at the start of the time period with LULC and its associated carbon stock at the end of the time period, i. e. we subtract the associated carbon stock of the end from the carbon stock of the start.
For the carbon flow estimation, you can choose between three different sets of carbon stock values: (1) Carbon stock values from the BLUE model (Hansis et al., 2015), (2) higher carbon stock values from Hansis et al. (2015) based on Reick et al. (2010), and (3) carbon stock values from a database of the Carbon Dioxide Information Analysis Center (Houghton & Hackler, 2001).
The carbon stock values are based on different assumptions, particularly concerning the heterogeneity of LULC classes and temporal dimension of carbon flows caused by LULC change.
Therefore, uncertainties of the estimated carbon flows differ depending on the selected source of carbon stock values.
For details, please consult the cited publications.

**Table 1. Carbon stocks of the LULC classes in tonnes/ha**

| LULC Class   | Carbon stock [tonnes/ha] |
|:-------------|-------------------------:|
| forest       |                    253.0 |
| grass        |                    161.5 |
| farmland     |                    108.0 |
| built-up     |                     71.0 |