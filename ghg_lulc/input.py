from datetime import date
from typing import Dict, Optional

import geojson_pydantic
import shapely
from pydantic import BaseModel, Field, condate, confloat, field_validator, model_validator

from ghg_lulc.utils import GhgStockSource


class ComputeInput(BaseModel):
    aoi: geojson_pydantic.Feature[geojson_pydantic.MultiPolygon, Optional[Dict]] = Field(
        title='Area of Interest',
        description='Area to calculate GHG emissions for.',
        validate_default=True,
        examples=[
            {
                'type': 'Feature',
                'properties': {},
                'geometry': {
                    'type': 'MultiPolygon',
                    'coordinates': [
                        [
                            [
                                [8.59, 49.36],
                                [8.78, 49.36],
                                [8.78, 49.44],
                                [8.59, 49.44],
                                [8.59, 49.36],
                            ]
                        ]
                    ],
                },
            }
        ],
    )
    date_before: condate(ge=date(2017, 1, 1), le=date.today()) = Field(
        title='Period Start',
        description='First timestamp of the period of analysis',
        examples=[date(2022, 5, 17)],
    )
    date_after: condate(ge=date(2017, 1, 1), le=date.today()) = Field(
        title='Period End',
        description='Last timestamp of the period of analysis',
        examples=[date(2023, 5, 31)],
    )
    classification_threshold: Optional[confloat(ge=0, le=100)] = Field(
        title='Minimum required classification confidence [%]',
        description='The LULC classification by an ML model '
        'has inherent uncertainties. This number '
        'defines the minimum confidence '
        'required by the user. Any prediction with '
        'confidence above this threshold will be '
        'classified "true", while those below '
        'will be classified as "unknown".',
        examples=[75],
        default=75,
    )
    ghg_stock_source: Optional[GhgStockSource] = Field(
        title='Literature Source for LULC GHG stock values',
        description='The set of GHG stock values used for the '
        'estimation of LULC change emissions. Three '
        'different sets of GHG stock values are available: '
        'Hansis et al. (2015), Reick et al. (2010), '
        'and Houghton & Hackler (2001). For '
        'more information on the GHG stock sources, '
        'please refer to the documentation.',
        examples=[GhgStockSource.HANSIS],
        default=GhgStockSource.HANSIS,
    )

    def get_geom(self) -> shapely.MultiPolygon:
        """Convert the input geojson geometry to a shapely geometry.

        :return: A shapely.MultiPolygon representing the area of interest defined by the user.
        """
        return shapely.geometry.shape(self.aoi.geometry)

    @field_validator('date_before', 'date_after')
    def check_month_year(cls, value):
        if not 5 <= value.month <= 9:
            raise ValueError('Dates must be within the months May to September.')
        return value

    @model_validator(mode='after')
    def check_order(self):
        if not self.date_after > self.date_before:
            raise ValueError('Period start must be before period end.')
        return self

    @model_validator(mode='after')
    def convert_threshold(self):
        self.classification_threshold = self.classification_threshold / 100
        return self
