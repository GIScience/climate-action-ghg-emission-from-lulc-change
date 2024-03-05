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