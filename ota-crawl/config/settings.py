from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trip Price API"
    app_env: str = "dev"
    app_debug: bool = True

    model_config = SettingsConfigDict(
        env_file=".ai.dev.env",
        env_file_encoding="utf-8",
        env_prefix="OTA_",
        extra="ignore",
    )


settings = Settings()
