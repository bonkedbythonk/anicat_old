from fastapi import APIRouter, HTTPException
from ...core.config.model import AppConfig
from ...core.constants import USER_CONFIG
from ...cli.config.generate import generate_config_toml_from_app_model
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_ctx():
    from ..main import ctx
    return ctx

@router.get("/")
async def get_config():
    """Get the current application configuration."""
    ctx = get_ctx()
    return ctx.config.model_dump(mode="json")

@router.patch("/")
async def update_config(updates: dict):
    """Update specific configuration fields."""
    try:
        logger.info("Received config update: %s", updates)
        # Prefer using the running context if initialized, otherwise load config from disk
        ctx = get_ctx()
        if not ctx.is_initialized():
            ctx = None

        if ctx is not None:
            config_dict = ctx.config.model_dump()
        else:
            from ...cli.config import ConfigLoader as _ConfigLoader
            loader = _ConfigLoader()
            current = loader.load(allow_setup=False)
            config_dict = current.model_dump()
        
        # Merge updates
        for section, fields in updates.items():
            if section in config_dict and isinstance(fields, dict):
                config_dict[section].update(fields)
            else:
                # If it's a top-level field or new section
                config_dict[section] = fields
        
        # Validate new config
        new_config = AppConfig.model_validate(config_dict)
        
        # Generate TOML and save to disk
        toml_content = generate_config_toml_from_app_model(new_config)
        USER_CONFIG.write_text(toml_content, encoding="utf-8")
        
        # Attempt to update the in-memory context if available
        if ctx is not None:
            try:
                ctx.config = new_config
                ctx.data_version += 1
            except Exception:
                logger.info("Active context exists but failed to refresh in-memory config.")
        else:
            logger.info("No active context to refresh; updated config written to disk only.")

        # If the token was updated, reset the media_api instance and force online status
        if "anilist" in updates and "token" in updates["anilist"] and ctx is not None:
            ctx._media_api = None
            ctx.is_offline = False
        
        logger.info("Config updated successfully")
        # Return the new config so frontend can refresh state immediately
        return {"status": "updated", "config": new_config.model_dump(mode="json")}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("Failed to update config: %s\n%s", e, tb)
        # Return structured error to help frontend show messages
        raise HTTPException(status_code=400, detail={"error": str(e), "trace": tb})


@router.get("/options")
async def get_config_options():
    """Return allowed option values for UI dropdowns.

    This keeps frontend option lists in sync with server-supported values.
    """
    return {
        "stream": {
            "quality": ["1080", "720", "480", "360"],
            "player_type": ["embedded", "external"],
        },
        "general": {
            "provider": ["animepahe"],
            "manga_provider": ["mangakatana"],
            "media_api": ["anilist", "jikan"],
            "time_format": ["12h", "24h"],
            "update_branch": ["stable", "nightly"],
        },
    }
