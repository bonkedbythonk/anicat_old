from anicat_media.core.config import AppConfig
from anicat_media.cli.config.generate import generate_config_toml_from_app_model

config = AppConfig()
print(generate_config_toml_from_app_model(config))
