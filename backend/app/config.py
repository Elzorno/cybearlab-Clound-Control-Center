import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "ISCS1800 Unified Admin + Grader API")
    app_version: str = os.getenv("APP_VERSION", "0.2.0")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./iscs1800.db")
    token_ttl_seconds: int = int(os.getenv("TOKEN_TTL_SECONDS", "28800"))
    bootstrap_admin_username: str = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
    bootstrap_admin_password: str = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "change-me-now")
    execution_mode: str = os.getenv("EXECUTION_MODE", "mock")
    command_timeout_seconds: int = int(os.getenv("COMMAND_TIMEOUT_SECONDS", "120"))

    script_add_student: str = os.getenv("SCRIPT_ADD_STUDENT", "/usr/local/sbin/iscs1800-add-student")
    script_reset_password: str = os.getenv("SCRIPT_RESET_PASSWORD", "/usr/local/sbin/iscs1800-reset-password")
    script_disable_student: str = os.getenv("SCRIPT_DISABLE_STUDENT", "/usr/local/sbin/iscs1800-disable-student")
    script_bulk_add: str = os.getenv("SCRIPT_BULK_ADD", "/usr/local/sbin/iscs1800-bulk-add")
    script_fix_perms: str = os.getenv("SCRIPT_FIX_PERMS", "/usr/local/sbin/iscs1800-fix-perms")
    script_https_students: str = os.getenv("SCRIPT_HTTPS_STUDENTS", "/usr/local/sbin/iscs1800-enable-https-students")
    script_https_admin: str = os.getenv("SCRIPT_HTTPS_ADMIN", "/usr/local/sbin/iscs1800-enable-https-admin")
    script_https_wildcard: str = os.getenv("SCRIPT_HTTPS_WILDCARD", "/usr/local/sbin/iscs1800-enable-https-wildcard")
    upload_root_dir: str = os.getenv("UPLOAD_ROOT_DIR", "/tmp/iscs1800/uploads")
    max_roster_upload_bytes: int = int(os.getenv("MAX_ROSTER_UPLOAD_BYTES", str(20 * 1024 * 1024)))
    grader_max_pages: int = int(os.getenv("GRADER_MAX_PAGES", "30"))
    grader_http_timeout_seconds: int = int(os.getenv("GRADER_HTTP_TIMEOUT_SECONDS", "20"))
    grader_validator_endpoint: str = os.getenv("GRADER_VALIDATOR_ENDPOINT", "https://validator.w3.org/nu/")


settings = Settings()
