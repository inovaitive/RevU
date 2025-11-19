from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class OrganizationBase(BaseModel):
    name: str
    domain: Optional[str] = None
    tier: str = "free"


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
