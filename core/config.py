from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Type, Dict

logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def _bool_env(name: str, default: bool = False) -> bool:
    """Return boolean value from environment variable."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    """Return int value from environment variable, fallback to default on error."""
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class BaseConfig:
    """Base configuration shared across environments."""
    # file types allowed for upload
    ALLOWED_EXTENSIONS: frozenset = frozenset({"csv"})

    # project paths
    BASE_DIR: Path = PROJECT_ROOT
    DATA_DIR: Path = BASE_DIR / "data"
    MODEL_DIR: Path = BASE_DIR / "ml" / "models"
    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", str(MODEL_DIR / "insurance_model.joblib")))
    UPLOAD_FOLDER: Path = DATA_DIR / "uploads"

    # app behavior
    DEBUG: bool = _bool_env("FLASK_DEBUG", False)
    MAX_CONTENT_LENGTH: int = _int_env("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)  # bytes

    # security / cookies
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-key-change-in-prod")
    SESSION_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True

    # database
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # misc
    CURRENCY: str = os.getenv("CURRENCY", "USD")

    @classmethod
    def ensure_dirs(cls) -> None:
        """Create required directories if they don't exist; log failures."""
        for p in {cls.MODEL_DIR, cls.DATA_DIR, cls.UPLOAD_FOLDER}:
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                logger.debug("Failed to create directory %s: %s", p, exc)


class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False
    REMEMBER_COOKIE_SECURE: bool = False
    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{BaseConfig.BASE_DIR / 'db_dev.sqlite3'}"


class ProductionConfig(BaseConfig):
    DEBUG: bool = False
    SESSION_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True
    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{BaseConfig.BASE_DIR / 'db_prod.sqlite3'}"

    @classmethod
    def ensure_production_safety(cls) -> None:
        """Check production-critical settings and log warnings or raise."""
        if cls.SECRET_KEY == "dev-key-change-in-prod":
            logger.error("SECRET_KEY is using the development default in production. Set SECRET_KEY in environment.")
            # Optionally raise RuntimeError to fail fast:
            # raise RuntimeError("SECRET_KEY must be set in production environment.")


config_by_name: Dict[str, Type[BaseConfig]] = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> Type[BaseConfig]:
    """Return config class by name or FLASK_ENV; ensure directories exist."""
    key = (name or os.getenv("FLASK_ENV") or "default").lower()
    cfg = config_by_name.get(key, config_by_name["default"])
    cfg.ensure_dirs()
    if key == "production":
        # optional safety checks for production
        try:
            cfg.ensure_production_safety()
        except AttributeError:
            pass
    return cfg


# Backwards compatibility alias
Config = BaseConfig