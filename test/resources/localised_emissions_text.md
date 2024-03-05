## Map: Localized emissions - GHG emissions per pixel due to LULC change (t)

The LULC change emissions per pixel (t) during the observation period are shown in this map.
Emissions are estimated in the following way: To each LULC, specific carbon stocks are assigned, e.g. a forest stores more carbon than a meadow or a settlement.
The carbon stocks of the selected source are shown in Table 1.
These carbon stocks encompass soil and vegetation carbon, providing an average measure of carbon stored per hectare.
Our method compares LULC and its associated carbon stock at time stamp 1 with LULC and its associated carbon stock at time stamp 2, i. e. we subtract the associated carbon stock of time stamp 2 from the carbon stock of time stamp 1.
The resulting emission factors are shown in Table 2.
Negative emission values indicate carbon sequestration resulting from the LULC change.

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