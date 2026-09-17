The model’s confidence for all areas that have been assigned a LULC class lies above the classification confidence threshold of 75 %.
All areas where the model’s confidence lies below the threshold have been classified as “unknown”.

LULC is classified by a semantic segmentation model called [SegFormer](https://arxiv.org/abs/2105.15203) using OpenStreetMap LULC polygons, images from [Sentinel 1 and Sentinel 2](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/The_Sentinel_missions), as well as a digital elevation model.
Since clouds may obstruct the area or parts of it in a single image, the model uses images from the entire month of July in the selected year.
Aside from cloud cover, the LULC classification is subject to multiple inaccuracies which can lead to misidentified change in unchanged regions, such as the salt-and-pepper effect[^1], atmospheric influences[^2], mixed pixels[^3], etc.

[^1]: The salt-and-pepper effect occurs often in pixel-based image classifications.
If the images are noisy or there are only few, very general classes (as in this classification), adjacent pixels can appear to be randomly assigned to different classes, looking as if salt and pepper were sprinkled over the image.

[^2]: Atmospheric influences such as scattering and absorption of sunlight by atmospheric molecules and aerosols that cause haziness in the image can change the image color in one of the points-in-time, even if there was no LULC change.

[^3]: Mixed pixels occur if the land cover varies within the pixel.
The pixel size of our data is 10 m, so this occurs often, especially at the borders of different LULC classes.
At the edge between two LULC classes, a pixel might be assigned to class _A_ at the start and to class _B_ at the end of the analysis period.