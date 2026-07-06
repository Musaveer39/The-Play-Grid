# backend/app/core/dependencies.py
from typing import Optional
from fastapi import Depends, Query
from datetime import date, datetime

class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page")
    ):
        self.page = page
        self.limit = limit
        self.offset = (page - 1) * limit

class TurfFilters:
    def __init__(
        self,
        city: Optional[str] = None,
        sport_type: Optional[str] = None,
        date: Optional[date] = None,
        min_price: Optional[float] = Query(None, ge=0),
        max_price: Optional[float] = Query(None, ge=0),
        search: Optional[str] = None
    ):
        self.city = city
        self.sport_type = sport_type
        self.date = date
        self.min_price = min_price
        self.max_price = max_price
        self.search = search