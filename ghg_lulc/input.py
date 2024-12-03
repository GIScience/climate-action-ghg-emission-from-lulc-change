from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, condate, confloat, field_validator, model_validator

from ghg_lulc.utils import GhgStockSource


class ComputeInput(BaseModel):
    date_before: condate(ge=date(2017, 1, 1), le=date.today()) = Field(
        title='Period Start',
        description='First timestamp of the period of analysis. Currently, only months from May to September are '
        'possible.',
        examples=[date(2022, 5, 17)],
    )
    date_after: condate(ge=date(2017, 1, 1), le=date.today()) = Field(
        title='Period End',
        description='Last timestamp of the period of analysis. Currently, only months from May to September are '
        'possible.',
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
        title='Scientific source for LULC GHG stock values',
        description='Please select a scientific source for the GHG stock values used in estimating LULC change '
        'emissions.'
        'For more information on the GHG stock sources, please refer to the documentation',
        examples=[GhgStockSource.HANSIS],
        default=GhgStockSource.HANSIS,
    )

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
