from datetime import datetime

from pydantic import BaseModel, Field, conint, model_validator

from ghg_lulc.utils import GhgStockSource


class ComputeInput(BaseModel):
    year_before: conint(ge=2017, le=datetime.now().year - 2) = Field(
        title='Start',
        description=f'First year of the period of analysis. Must be between 2017 and {datetime.now().year - 2}. '
        f'Satellite images from the month July of the selected year are used for LULC classification.',
        examples=[2017],
    )
    year_after: conint(ge=2018, le=datetime.now().year - 1) = Field(
        title='End',
        description=f'Last year of the period of analysis. Must be between 2018 and {datetime.now().year - 1}. '
        f'Satellite images from the month July of the selected year are used for LULC classification.',
        examples=[2024],
    )
    ghg_stock_source: GhgStockSource = Field(
        title='Source of LULC carbon stock values',
        description='Please select the source of the carbon stock values used in estimating LULC change emissions. '
        'For more information on the carbon stock sources, please refer to the documentation.',
        examples=[GhgStockSource.HANSIS],
        default=GhgStockSource.HANSIS,
    )

    @model_validator(mode='after')
    def check_order(self):
        if not self.year_after > self.year_before:
            raise ValueError('Period start must be before period end')
        return self
