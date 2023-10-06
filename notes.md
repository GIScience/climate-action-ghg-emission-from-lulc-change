## Input:
- dictionary with start date, end date, AOI
- AOI: for now, bounding box defined by 4 coordinates
- **extend AOI input by geojson file denoting the area?**

## Output:
- **tiff file showing the lulc changes?**
- **CSV with the following info:**
	+ total LULC change area (ha)
	+ Area by LULC change type, e.g. agriculture to urban (ha)
	+ total LULC change emissions
	+ LULC change emissions by LULC change type, e.g. agriculture to urban
- **Should we account for LULC imissions, e.g. agriculture to forest or only emissions? (In my master thesis I did only emissions but I can just do the emissions vice versa. e.g. if agriculture to urban would lead to emissions of 40 t/ha, urban to agriculture would lead to a carbon sink of 40 t/ha)**

## Method
**How do I access the LULC utility?** Do I just follow the instructions in the Gitlab to set it up?

**Which land use classes are used again? Urban, agriculture, forest?**

**Should it be possible to select an individual LULC change and get infos about it like  emissions, change type, etc.? Then conversion to vector would be needed**


### Function to obtain the LULC
- input: start date, end date, AOI
- action: request from LULC API
- output: 2 tiffs with LULC

### Function to derive LULC changes
- input: 2 tiffs with LULC
- action: first transform to numpy array. perform a calculation on the tiffs: Check if there is a LULC change in each cell and what kind of LULC change. Then it assigns an emission factor directly to the cell.
- output: numpy array with emission factor for each cell.

### Function to generate tiff with changes
- input: numpy array with emission factor for each cell
- action: save emission map as geotiff. Each emission factor represents a certain LULC change type, so the tiff shows what kind of LULC change happened and at the same time the emissions per ha of these changes (explain in the documentation)
- output: None

### Function to calculate total LULC change area (ha)
- input: numpy array with emission factor for each cell
- action: calculate total LULC change area (ha) by summing up areas of all cells where emission factor != 0)
- output: total LULC change area (ha)

### Function to calculate area by LULC change type
- input: numpy array with emission factor for each cell
- action: group by emission factor and sum up areas of all cells for each group. (convert to pandas dataframe beforehand?)
- output: dataframe with columns LULC change type and change area

### Function to calculate absolute LULC change emissions per cell
- input: numpy array with emission factor for each cell
- action: calculate absolute LULC change emissions per cell by multiplying emission factor with cell area
- output: numpy array with absolute LULC change emissions per cell

### Function to calculate total LULC change emissions
- input: numpy array with absolute LULC change emissions per cell
- action: calculate total LULC change emissions by summing up emissions of all cells
- output: total LULC change emissions

### Function to calculate LULC change emissions by LULC change type
- input: numpy array with absolute LULC change emissions per cell
- action: calculate LULC change emissions by LULC change type by grouping the cells by their emission value and then summing up the emissions for each group. convert to pandas df beforehand?
- output: dataframe with columns LULC change type and change emissions

### Function to generate csv
- input: df with columns LULC change type, change area, change emissions
- action: add a row sum and add the total change area and emissions there
- export df as csv
- output: none