import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "ISCS1800 Unified Admin + Grader API")
    app_version: str = os.getenv("APP_VERSION", "0.2.0")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./iscs1800.db")
    token_ttl_seconds: int = int(os.getenv("TOKEN_TTL_SECONDS", "28800"))
    bootstrap_admin_username: str = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
    bootstrap_admin_password: str = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "change-me-now")


settings = Settings()
