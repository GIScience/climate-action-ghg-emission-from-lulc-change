# LULCC Plugin Methodology/Disclaimer

## Methodology

The plugin initiates the emission estimation process by obtaining two distinct Land Use and Land Cover (LULC) classifications at the beginning and end of the chosen analysis period using a custom LULC classification model based on Sentinel remote sensing data.
Subsequently, the plugin identifies LULC changes that occurred during this period.
Carbon emissions associated with these changes are calculated by subtracting the carbon stocks (measured in t/ha) of the initial and final LULC classes for each specific change type in a specific vegetation zone, e.g. temperate coniferous forest (e.g. carbon stock forest – carbon stock meadow).
These carbon stocks encompass estimated soil and vegetation carbon content, providing an average measure of carbon stored per hectare.
For most of the LULC classes, different carbon stock values can be found in the literature (see section “Selection of carbon stock values” for more information).
At the moment, it is possible to use the plugin with three different sets of carbon stocks (Table 1).
Emissions (in t/ha) are calculated by subtracting the final from the initially assigned carbon stocks.
The resulting emission values of the different LULC change types are shown in Table 2.
Positive emission values indicate carbon emissions resulting from the LULC change.
Negative emission values indicate carbon sequestration resulting from the LULC change.
It is assumed that each location experiences a maximum of one LULC change during the analysis period.

**Table 1. Carbon stocks of the LULC classes in t/ha**
|LULC class|Hansis et al. (2015)|Hansis et al. (2015), higher carbon values|Houghton & Hackler (2001)|
|----------|--------------------|------------------------------------------|-------------------------|
|Forest    |253                 |310.75                                    |253                      |
|Grass     |161.5               |286                                       |196                      |
|Farmland  |108                 |168                                       |160                      |
|Built-up  |71                  |71                                        |71                       |

##### The carbon stock value for settlement is a combination of the soil carbon value 60 t/ha (Bradley et al., 2006) and vegetation carbon value 11 t/ha (Strohbach & Haase, 2012).

**Table 2. Carbon emissions of the LULC change types in t/ha**
|LULC change type    |Hansis et al. (2015)|Hansis et al. (2015), higher carbon values|Houghton & Hackler (2001)|
|--------------------|--------------------|------------------------------------------|-------------------------|
|Built-up to forest  |-182                |-239.75                                   |-182                     |
|Farmland to forest  |-145                |-142.75                                   |-93                      |
|Grass to forest     |-91.5               |-24.75                                    |-57                      |
|Built-up to grass   |-90.5               |-215                                      |-125                     |
|Built-up to farmland|-37                 |-97                                       |-89                      |
|Farmland to grass   |-53.5               |-118                                      |-36                      |
|Grass to farmland   |53.5                |118                                       |36                       |
|Farmland to built-up|37                  |97                                        |89                       |
|Grass to built-up   |90.5                |215                                       |125                      |
|Forest to grass     |91.5                |24.75                                     |57                       |
|Forest to farmland  |145                 |142.75                                    |93                       |
|Forest to built-up  |182                 |239.75                                    |182                      |

The LULC classification has inherent uncertainties.
Thus, it is possible to set a minimum classification confidence, by which the user can define the required minimum level of confidence for their analysis.
Any emission estimate with a modeled confidence above this threshold will be assumed to be "true", all results exhibiting lower confidence will be classified as "unknown".
Since the LULC classification model has been trained for the summer months, it should only be used for dates from May to September.

Besides localized carbon emissions, total change area and change emissions by LULC change type, size of the area of interest, share of change areas of the area of interest, area of emitting changes, share of emitting change area of the total change area, area of changes representing carbon sinks, share of carbon sink change area of the total change area, total gross emissions, sinks, and net emissions are calculated.
Gross emissions are the total LULC change emissions of carbon to the atmosphere.
The term carbon sink refers to the total carbon sequestration as a result of LULC change.
Net emissions are the subtraction of emissions by carbon sinks.

## Selection of carbon stock values

For ‘settlement’, all sets of carbon stock values use the same carbon stock value: a combination of the vegetation carbon stock estimated for Leipzig, which is 11 t/ha (Strohbach & Haase, 2012), and a soil carbon estimation for suburban areas in England, which is 60 t/ha (Bradley et al., 2005).
These carbon stocks were chosen because the initial version of this plugin is based on a study done in the Central and Western European context (Ulrich et al., 2023), for which these were the most suitable carbon stock estimates available.
Leipzig can be seen as representative for many cities in Western and Central Europe.
The estimated soil carbon content for suburban areas was chosen because the settlement class contains not only dense city centers, but also many suburban and rural settlements with much green space.
The carbon stocks might have to be adapted when applying this plugin outside Central and Western Europe.

For the classes farmland, meadow, and forest, the carbon stock values are taken from the BLUE model (Hansis et al., 2015) and from a database of the Carbon Dioxide Information Analysis Center (Houghton & Hackler, 2001).
The higher carbon stock values from Hansis et al. (2015) are based on Reick et al. (2010).
For forest in temperate climates, these sources offer carbon stock values for primary and secondary forests, as well as deciduous broadleaf forests and evergreen or deciduous coniferous forests.
The carbon stock values for secondary evergreen coniferous forests were chosen because the first area of application for this plugin is Germany, where nearly all forests are secondary forests with spruce and pine as dominant tree species (NABU, 2024).
For other study areas, different carbon stock values might be more suitable.
Therefore, it is recommended to use this version of the LULC change plugin only in areas with temperate climate.

## Potential sources of error

The method-inherent error of the LULC change emission plugin is influenced by uncertainties of the LULC classification model and the emission factors.
Since the actual error depends on the selected area of interest and LULC change period, it is difficult to quantify.
The main error sources are discussed in this section.

### LULC classification

The confidence of the LULC classification is influenced by clouds, which may obstruct the area or parts of it in a single image.
Aside from cloud cover, the LULC classification is subject to multiple inaccuracies which can potentially create random change pixels for unchanged regions, such as the (1) salt-and-pepper effect, (2) atmospheric influences, (3) mixed pixels etc.
(1) The salt-and-pepper effect occurs often in pixel-based image classifications.
If the images are noisy or there are only few, very general classes, as in this case, it can happen that adjacent pixels are seemingly randomly assigned to different classes so that it looks as if salt and pepper were sprinkled over the image.
(2) Atmospheric influences such as scattering and absorption of sunlight by atmospheric molecules and aerosols that cause haziness in the image can change the image color in one of the points-in-time, even if there was no LULC change.
(3) Mixed pixels occur if the land cover varies within the pixel.
This may happen especially at the edges between two LULC classes, where a pixel might be assigned to class A at the first point-in-time and to class B at the second point-in-time, because it can only be assigned to one class.

### Emission factors

The carbon stock values were derived by measuring vegetation biomass and soil carbon in plots of land that were deemed representative for the different vegetation types (Olson, 1983; Schlesinger, 1977).
They represent assumed averages for each LULC class and cannot capture the heterogeneity of the LULC classes.
For example, the forest class covers everything from a sparse pine plantation to a lush beech forest.

Additionally, the LULC change emissions have a temporal component, which we do not capture.
For example, when forest is cleared, much of the carbon will remain in the wood of the trees for many years, even decades, if the wood is used to e.g. build furniture.
Also, not all soil carbon is emitted.
In the plugin however, the LULC change emissions are estimated assuming pre- and post-change carbon stocks reach equilibrium directly, ignoring temporal delays (Hansis et al., 2015).
In other words, the plugin assumes that all of the carbon related to a LULC change is emitted at once, including soil carbon.
This means that our calculated emissions can be regarded as maximum values, the real carbon stock changes will often be lower and/or emitted over a longer timespan.

The emission factors only account for emissions caused by vegetation removal (e.g. clearing of forest for urban development).
They do not include subsequent emissions caused by e.g. construction of buildings.
With respect to this, real emissions will thus be higher.
Also, we only have emission factors for LULC changes between the classes forest, meadow, farmland, and settlement.
However, the LULC classification additionally includes the classes permanent crops and water.
For all areas that fall into one of these two classes at either timestamps, we cannot estimate the LULC change emissions.

## References

Bradley, R. i., Milne, R., Bell, J., Lilly, A., Jordan, C., & Higgins, A. (2005). A soil carbon and land use database for the United Kingdom. Soil Use and Management, 21(4), 363–369. [https://doi.org/10.1079/SUM2005351](https://doi.org/10.1079/SUM2005351)

Hansis, E., Davis, S. J., & Pongratz, J. (2015). Relevance of methodological choices for accounting of land use change carbon fluxes. Global Biogeochemical Cycles, 29(8), 1230–1246. [https://doi.org/10.1002/2014GB004997](https://doi.org/10.1002/2014GB004997)

Houghton, R. A., Hackler, J. L., & Cushman, R. M. (2001). Carbon flux to the atmosphere from land-use changes: 1850 to 1990. Oak Ridge: Carbon Dioxide Information Center, Environmental Sciences Division, Oak Ridge National Laboratory.

NABU. (2024). Zahlen und Fakten ... Zum Wald in Deutschland und weltweit. [https://www.nabu.de/natur-und-landschaft/waelder/lebensraum-wald/13284.html](https://www.nabu.de/natur-und-landschaft/waelder/lebensraum-wald/13284.html)

Olson, J. S. (1983). Carbon in Live Vegetation of Major World Ecosystems. U.S. Department of Energy.

Reick, C., Raddatz, T., Pongratz, J., & Claussen, M. (2010). Contribution of anthropogenic land cover change emissions to pre-industrial atmospheric CO2. Tellus B: Chemical and Physical Meteorology, 62(5), 329-336. [https://doi.org/10.1111/j.1600-0889.2010.00479.x](https://doi.org/10.1111/j.1600-0889.2010.00479.x)

Schlesinger, W. H. (1977). Carbon balance in terrestrial detritus. Annual Review of Ecology and Systematics, 8, 51–81. [https://doi.org/10.1146/annurev.es.08.110177.000411](https://doi.org/10.1146/annurev.es.08.110177.000411)

Strohbach, M. W., & Haase, D. (2012). Above-ground carbon storage by urban trees in Leipzig, Germany: Analysis of patterns in a European city. Landscape and Urban Planning, 104(1), 95–104. [https://doi.org/10.1016/j.landurbplan.2011.10.001](https://doi.org/10.1016/j.landurbplan.2011.10.001)

Ulrich, V., Schultz, M., Lautenbach, S., & Zipf, A. (2023). Carbon fluxes related to land use and land cover change in Baden-Württemberg. Environmental Monitoring and Assessment, 195(5), 616. [https://doi.org/10.1007/s10661-023-11141-9](https://doi.org/10.1007/s10661-023-11141-9)
