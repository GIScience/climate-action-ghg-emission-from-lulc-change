# Methodology

The operator initiates the process by obtaining two distinct Land Use and Land Cover (LULC) classifications at the
beginning and end of the chosen observation period using
the [LULC utility](https://gitlab.gistools.geog.uni-heidelberg.de/climate-action/lulc-utility). Subsequently, the
operator identifies LULC changes that occurred during this period. Carbon emissions associated with these changes are
calculated by comparing the carbon stocks (measured in t/ha) of the initial and final LULC classes for each specific
change type. These carbon stocks encompass soil and vegetation carbon, providing an average measure of carbon stored per
hectare.

The carbon stocks are 71 t/ha for the class settlement, 106 t/ha for the class farmland, 107.5 t/ha for the class meadow
and 227 t/ha for the class forest. For the class settlement, the carbon stock value is a combination of the vegetation
carbon stock estimated for Leipzig, which is 11 t/ha (Strohbach & Haase 2012), and a soil carbon estimation for suburban
areas in England, which is 60 t/ha (Bradley et al. 2006). These carbon stocks were chosen because this methodology is
based on a study done in the central- and Western European context (Ulrich et al. 2023). Leipzig can be seen as
representative of many cities in west and central Europe. The estimated soil carbon content for suburban areas was
chosen because the settlement class contains dense city centres and many suburban and rural settlements with much green
space. The carbon stocks might have to be adapted when applying this operator outside central and Western Europe. The
carbon stock value that is utilized for farmland consists of the vegetation carbon stock from the BLUE model, which is 5
t/ha (Hansis et al. 2015) and the soil carbon stock from a database of the Carbon Dioxide Information Analysis Center,
which is 101 t/ha (Houghton & Hackler 2001). The carbon stock for meadow is a combination of the vegetation carbon
stock (7 t/ha) and the soil carbon stock (100.5 t/ha) of pasture from the BLUE model (Hansis et al. 2015). The carbon
stock for forest consists of the vegetation carbon stock of secondary deciduous forest from the BLUE model, which is 100
t/ha (Hansis et al. 2015) and the soil carbon stock of secondary temperate deciduous forest from a database of the
Carbon Dioxide Information Analysis Center, which is 127 t/ha (Houghton & Hackler 2001). The carbon stocks for secondary
deciduous forest were chosen because the original study area in Western Europe has little to no primary forests, and
deciduous forest is the natural vegetation in most of the area. For other study areas, different carbon stock values
might be more suitable.

LULC change emissions are estimated assuming pre- and post-change carbon stocks reach equilibrium, ignoring temporal
delays (Hansis et al., 2015). Emissions (in t/ha) are calculated by subtracting the final from the initial assigned
carbon stocks. The resulting emission values of the different LULC change types are shown in Table 1. Negative emission
values indicate carbon sequestration resulting from the LULC change. It is assumed that each location experiences a
maximum of one LULC change during the observation period.

### Table 1. Carbon emissions of the LULC change types in t/ha

| LULC change type                         | Carbon emissions [t/ha] |
|------------------------------------------|-------------------------|
| settlement to forest                     | -156                    |
| farmland to forest                       | -121                    |
| meadow to forest                         | -119.5                  |
| settlement to meadow                     | -36.5                   |
| settlement to farmland                   | -35                     |
| farmland to meadow                       | -1.5                    |
| default value or change from or to water | unknown                 |
| no change                                | 0                       |
| meadow to farmland                       | 1.5                     |
| farmland to settlement                   | 35                      |
| meadow to settlement                     | 36.5                    |
| forest to meadow                         | 119.5                   |
| forest to farmland                       | 121                     |
| forest to settlement                     | 156                     |

Besides the carbon emissions in t/ha, the total change area by LULC change type, the total change emissions by LULC
change type, and the total change area, as well as the total net emissions, gross emissions, and carbon sink, are
calculated. Net emissions are the combination of emissions and carbon sinks, gross emissions are the total LULC change
emissions of carbon to the atmosphere, and carbon sink means the total carbon sequestration as a result of LULC change.