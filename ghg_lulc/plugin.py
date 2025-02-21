import logging.config

import matplotlib
from climatoology.app.plugin import start_plugin
from climatoology.utility.LULC import LulcUtility
from pydantic_settings import BaseSettings, SettingsConfigDict

from ghg_lulc.operator_worker import GHGEmissionFromLULC

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    lulc_host: str
    lulc_port: int
    lulc_path: str

    mplbackend: str = 'agg'

    model_config = SettingsConfigDict(env_file='.env')


def init_plugin(settings: Settings) -> int:
    lulc_utility = LulcUtility(
        host=settings.lulc_host,
        port=settings.lulc_port,
        path=settings.lulc_path,
    )
    operator = GHGEmissionFromLULC(lulc_utility)

    log.info(f'Running plugin: {operator.info().name}')
    return start_plugin(operator=operator)


if __name__ == '__main__':
    settings = Settings()

    matplotlib.use(settings.mplbackend)

    exit_code = init_plugin(settings)
    log.info(f'Plugin exited with code {exit_code}')
