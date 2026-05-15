from fastapi import APIRouter, HTTPException
from ...core.config.model import AppConfig
from ...core.constants import USER_CONFIG
from ...cli.config.generate import generate_config_toml_from_app_model

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
        ctx = get_ctx()
        # Load current config dict
        config_dict = ctx.config.model_dump()
        
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
        
        # Update current context
        ctx.config = new_config
        ctx.data_version += 1

        # If the token was updated, reset the media_api instance and force online status
        if "anilist" in updates and "token" in updates["anilist"]:
            ctx._media_api = None
            ctx.is_offline = False
        
        return {"status": "updated"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
