from datetime import datetime

from pydantic import BaseModel, Field, conint, model_validator

from ghg_lulc.components.utils import GhgStockSource


class ComputeInput(BaseModel):
    start_year: conint(ge=2017, le=datetime.now().year - 2) = Field(
        title='Start',
        description=f'First year of the period of analysis. Must be between 2017 and {datetime.now().year - 2}. '
        f'Satellite images from the month July of the selected year are used for LULC classification.',
        examples=[2017],
    )
    end_year: conint(ge=2018, le=datetime.now().year - 1) = Field(
        title='End',
        description=f'Last year of the period of analysis. Must be between 2018 and {datetime.now().year - 1}. '
        f'Satellite images from the month July of the selected year are used for LULC classification.',
        examples=[datetime.now().year - 1],
    )
    carbon_stock_source: GhgStockSource = Field(
        title='Source of LULC carbon stock values',
        description='Please select the source of the carbon stock values used in estimating carbon flows from LULC change.',
        examples=[GhgStockSource.HANSIS],
        default=GhgStockSource.HANSIS,
    )

    @model_validator(mode='after')
    def check_order(self):  # dead: disable
        if not self.end_year > self.start_year:
            raise ValueError('Period start must be before period end')
        return self
