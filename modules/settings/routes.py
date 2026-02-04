from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database.base import get_db
from modules.users.models import User
from modules.settings.models import AppSetting
from shared.dependencies import require_admin
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/public/{group}")
def get_public_settings(
    group: str,
    db: Session = Depends(get_db)
):
    """
    Get public settings by group (no auth required).
    """
    settings = db.query(AppSetting).filter(
        AppSetting.group == group,
        AppSetting.is_public == True
    ).all()
    
    result = {}
    for setting in settings:
        try:
            result[setting.key] = json.loads(setting.value)
        except:
            result[setting.key] = setting.value
            
    return result

@router.get("/{group}")
def get_settings_by_group(
    group: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all settings by group (Admin only).
    """
    settings = db.query(AppSetting).filter(AppSetting.group == group).all()
    
    result = {}
    for setting in settings:
        try:
            result[setting.key] = json.loads(setting.value)
        except:
            result[setting.key] = setting.value
            
    return result

@router.put("/{group}")
def update_settings(
    group: str,
    settings_data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update settings for a group.
    """
    try:
        for key, value in settings_data.items():
            # Check if setting exists
            setting = db.query(AppSetting).filter(
                AppSetting.key == key, 
                AppSetting.group == group
            ).first()
            
            json_value = json.dumps(value)
            
            if setting:
                setting.value = json_value
            else:
                # Create new setting
                new_setting = AppSetting(
                    key=key,
                    value=json_value,
                    group=group,
                    is_public=True, # Default to public for now for onboarding
                    description=f"Setting for {key}"
                )
                db.add(new_setting)
        
        db.commit()
        return {"success": True, "message": "Settings updated successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
