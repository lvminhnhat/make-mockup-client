import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class Base_task():
    id: str
    product_name: str
    product_type: str
    final_image: List [str] 
    status: str
    store: str
    downloaded_image_path: str
    message: str
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary."""
        return {
            "id": self.id,
            "product_name": self.product_name,
            "product_type": self.product_type,
            "final_image": self.final_image,
            "status": self.status,
            "store": self.store,
            "downloaded_image_path": self.downloaded_image_path,
            "message": self.message
        }
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Base_task':
        """Create a task from a dictionary."""
        return cls(
            id=data.get("id", ""),
            product_name=data.get("product_name", ""),
            product_type=data.get("product_type", ""),
            final_image=data.get("final_image", []),
            status=data.get("status", "pending"),
            store=data.get("store", ""),
            downloaded_image_path=data.get("downloaded_image_path", ""),
            message=data.get("message", "")
        )

class TaskCreate(BaseModel):
    id: str
    product_name: str
    product_type: str
    webhook_url: str = ""