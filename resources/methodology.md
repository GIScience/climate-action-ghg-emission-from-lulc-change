The LULC Change Emission Estimation Tool assesses carbon emissions associated with Land Use and Land Cover (LULC) changes in a selected area of interest over a specified observation period.
The methodology involves acquiring LULC classifications at the start and end of the period, identifying changes, and calculating emissions based on carbon stock differences between initial and final LULC classes.
The carbon stocks encompass soil and vegetation carbon, providing an average measure of carbon stored per hectare.
Various LULC change types are included and associated carbon emissions and sinks/sequestration (in t/ha) are calculated.
To each LULC, specific carbon stocks are assigned, e.g. a forest stores more carbon than a meadow or a settlement.
Our method thus compares LULC and its associated carbon stock at time stamp 1 with LULC and its associated carbon stock at time stamp 2, i. e. we subtract the associated carbon stock of time stamp 2 from the carbon stock of time stamp 1.
Since the selected carbon stock values are characteristic for areas with temperate climate, e.g. Central and Western Europe, the tool can only be used in these areas.

For the emission estimation, you can choose between three different sets of carbon stock values: (1) Carbon stock values from the BLUE model (Hansis et al., 2015), (2) higher carbon stock values from Hansis et al. (2015) based on Reick et al. (2010), and (3) carbon stock values from a database of the Carbon Dioxide Information Analysis Center (Houghton & Hackler, 2001).

The LULC classification has inherent uncertainties.
For example, it is influenced by clouds, which may obstruct the area or parts of it in a single image.
Aside from cloud cover, the LULC classification is subject to multiple inaccuracies which can potentially create random change pixels for unchanged regions, such as the salt-and-pepper effect, atmospheric influences, and mixed pixels.
Thus, it is possible to set a minimum classification confidence, which defines the minimum level of confidence required by the user.
Any prediction where the model's confidence lies above this threshold will be assumed to be "true", all classification exhibiting lower confidence will be classified as "unknown".
For example, if the minimum classification confidence is set to 100 %, only predictions where the model is 100 % certain will be included, which means that most of the area will probably be classified as "unknown".
On the other hand, if the minimum classification confidence is set to 0 %, all predictions will be included, no matter how uncertain they are.
In most cases, it is reasonable to use a minimum classification threshold between 70 % and 90 %.
Further uncertainties arise from emission factor assumptions, particularly concerning the heterogeneity of LULC classes and temporal dimension of LULC change emissions.
