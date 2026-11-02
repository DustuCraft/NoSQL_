"""Схемы входа/выхода API."""
from typing import Optional

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="Уникальный код объекта")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(0, ge=0)


class ItemUpdate(BaseModel):
    """Частичное обновление: передаются только изменяемые поля."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    price: Optional[float] = Field(None, ge=0)


class ItemOut(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    price: float = 0


class ErrorOut(BaseModel):
    detail: str
