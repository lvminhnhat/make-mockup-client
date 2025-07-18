from pydantic import BaseModel
from typing import Any, Optional, Dict

class APIResponseSchema(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[Dict] = None
    meta: Optional[Dict] = None
