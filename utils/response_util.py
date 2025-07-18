from fastapi.responses import JSONResponse
from typing import Any, Optional, Dict
import json
import re
from datetime import datetime
from schemas.api_response import APIResponseSchema


def create_slug(text: str) -> str:
    """
    Create a URL-friendly slug from text.
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().replace(' ', '-')
    
    # Remove special characters except hyphens and alphanumeric
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


def convert_datetime_to_isoformat(obj: Any) -> Any:
    """
    Recursively convert datetime objects to ISO format strings.
    This handles nested dictionaries and lists.
    """
    if isinstance(obj, dict):
        return {k: convert_datetime_to_isoformat(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_isoformat(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


def success_response(
    data: Any,
    message: str = "Operation successful",
    meta: Optional[Dict] = None,
    status_code: int = 200
) -> JSONResponse:
    """
    Create a successful JSON response with proper datetime serialization.
    """
    response_data = APIResponseSchema(
        success=True,
        message=message,
        data=data,
        meta=meta
    ).model_dump(exclude_none=True)
    
    # Convert datetime objects to ISO format strings
    response_data = convert_datetime_to_isoformat(response_data)
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )

def error_response(
    message: str,
    errors: Optional[Dict] = None,
    status_code: int = 400
) -> JSONResponse:
    """
    Create an error JSON response with proper datetime serialization.
    """
    if errors and isinstance(errors, str):
        errors = {"detail": errors}

    response_data = APIResponseSchema(
        success=False,
        message=message,
        errors=errors
    ).model_dump(exclude_none=True)
    
    # Convert datetime objects to ISO format strings
    response_data = convert_datetime_to_isoformat(response_data)

    return JSONResponse(
        status_code=status_code,
        content=response_data
    )