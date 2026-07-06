# backend/app/api/v1/turfs.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.core.security import get_current_user, get_current_owner
from app.core.dependencies import PaginationParams, TurfFilters

logger = logging.getLogger(__name__)
router = APIRouter()

# =============== SCHEMAS ===============

class TurfBase(BaseModel):
    name: str
    sport_type: str
    address: str
    city: str
    price_per_hour: float
    description: Optional[str] = None
    amenities: Optional[dict] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class TurfCreate(TurfBase):
    images: Optional[List[str]] = None

class TurfUpdate(BaseModel):
    name: Optional[str] = None
    sport_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    price_per_hour: Optional[float] = None
    description: Optional[str] = None
    amenities: Optional[dict] = None
    images: Optional[List[str]] = None
    is_active: Optional[bool] = None

class TurfResponse(TurfBase):
    id: str
    owner_id: str
    images: Optional[List[str]] = None
    rating: Optional[float] = None
    total_reviews: Optional[int] = None
    is_active: bool
    created_at: str
    updated_at: str

class PricingRuleCreate(BaseModel):
    rule_name: Optional[str] = None
    day_of_week: Optional[List[int]] = None
    day_type: Optional[str] = None  # 'all', 'weekday', 'weekend', 'custom'
    slot_type: Optional[str] = None  # 'all', 'day', 'night'
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    price: Optional[float] = 0.0  # Changed from price_multiplier to price
    custom_date: Optional[str] = None  # For custom date pricing

class SlotCreate(BaseModel):
    booking_date: date
    start_time: str
    end_time: str
    price: Optional[float] = None

class SlotResponse(BaseModel):
    id: str
    turf_id: str
    booking_date: str
    start_time: str
    end_time: str
    is_booked: bool
    price: Optional[float] = None

class GenerateSlotsRequest(BaseModel):
    start_date: date
    end_date: date
    slot_duration: int = 60
    start_time: str = "06:00"
    end_time: str = "22:00"

# =============== ENDPOINTS ===============

@router.get("/")
async def get_turfs(
    city: Optional[str] = None,
    sport_type: Optional[str] = None,
    date: Optional[date] = None,
    limit: int = 20,
    offset: int = 0
):
    """Get all turfs with filters"""
    try:
        db = get_db()
        
        query = db.table("turfs").select("*").eq("is_active", True)
        
        if city:
            query = query.ilike("city", f"%{city}%")
        if sport_type:
            query = query.eq("sport_type", sport_type)
        
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        logger.info(f"Found {len(result.data)} turfs")
        return result.data
        
    except Exception as e:
        logger.error(f"Error fetching turfs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching turfs: {str(e)}"
        )

@router.get("/", response_model=List[TurfResponse])
async def get_turfs_with_filters(
    filters: TurfFilters = Depends(),
    pagination: PaginationParams = Depends()
):
    """Get all turfs with filters"""
    db = get_db()
    
    try:
        query = db.table("turfs").select("*").eq("is_active", True)
        
        if filters.city:
            query = query.ilike("city", f"%{filters.city}%")
        if filters.sport_type:
            query = query.eq("sport_type", filters.sport_type)
        if filters.min_price:
            query = query.gte("price_per_hour", filters.min_price)
        if filters.max_price:
            query = query.lte("price_per_hour", filters.max_price)
        if filters.search:
            query = query.or_(
                f"name.ilike.%{filters.search}%,address.ilike.%{filters.search}%"
            )
        
        if filters.date:
            slots = db.table("slots") \
                .select("turf_id") \
                .eq("booking_date", filters.date.isoformat()) \
                .eq("is_booked", False) \
                .execute()
            
            available_turf_ids = [s["turf_id"] for s in slots.data]
            if available_turf_ids:
                query = query.in_("id", available_turf_ids)
        
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1)
        query = query.order("rating", desc=True)
        
        result = query.execute()
        return result.data
        
    except Exception as e:
        logger.error(f"Error fetching turfs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching turfs"
        )

@router.get("/{turf_id}", response_model=TurfResponse)
async def get_turf(turf_id: str):
    """Get turf details by ID"""
    db = get_db()
    
    try:
        result = db.table("turfs") \
            .select("*") \
            .eq("id", turf_id) \
            .eq("is_active", True) \
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turf not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching turf: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching turf details"
        )

@router.post("/", response_model=TurfResponse)
async def create_turf(
    turf_data: TurfCreate,
    current_user: dict = Depends(get_current_owner)
):
    """Create a new turf (Owner only)"""
    db = get_db()
    
    try:
        turf_dict = turf_data.model_dump()
        turf_dict["owner_id"] = current_user["id"]
        turf_dict["is_active"] = True
        
        result = db.table("turfs").insert(turf_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create turf"
            )
        
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error creating turf: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating turf"
        )

# backend/app/api/v1/turfs.py - Fix update_turf endpoint

# backend/app/api/v1/turfs.py - Fix update_turf endpoint

@router.put("/{turf_id}", response_model=TurfResponse)
async def update_turf(
    turf_id: str,
    turf_data: TurfUpdate,
    current_user: dict = Depends(get_current_owner)
):
    """Update turf details (Owner only)"""
    db = get_db()
    
    try:
        # Check ownership
        turf = db.table("turfs") \
            .select("owner_id") \
            .eq("id", turf_id) \
            .execute()
        
        # Check if turf exists
        if not turf.data or len(turf.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turf not found"
            )
        
        # Check ownership
        if turf.data[0]["owner_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't own this turf"
            )
        
        # Build update data - only include fields that are provided
        update_data = {}
        turf_dict = turf_data.model_dump(exclude_unset=True)
        
        for key, value in turf_dict.items():
            if value is not None:
                update_data[key] = value
        
        # If no fields to update, return current data
        if not update_data:
            return turf.data[0]
        
        logger.info(f"Updating turf {turf_id} with data: {update_data}")
        
        result = db.table("turfs") \
            .update(update_data) \
            .eq("id", turf_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update turf"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating turf: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating turf: {str(e)}"
        )
@router.get("/{turf_id}/slots", response_model=List[SlotResponse])
async def get_turf_slots(
    turf_id: str,
    booking_date: date,
    current_user: dict = Depends(get_current_user)
):
    """Get slots for a turf on a specific date"""
    db = get_db()
    
    try:
        turf = db.table("turfs") \
            .select("id") \
            .eq("id", turf_id) \
            .eq("is_active", True) \
            .execute()
        
        if not turf.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turf not found"
            )
        
        slots = db.table("slots") \
            .select("*") \
            .eq("turf_id", turf_id) \
            .eq("booking_date", booking_date.isoformat()) \
            .order("start_time") \
            .execute()
        
        return slots.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching slots: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching slots"
        )

# backend/app/api/v1/turfs.py - Fix generate_slots endpoint

# backend/app/api/v1/turfs.py - Updated generate_slots endpoint

@router.post("/{turf_id}/slots/generate")
async def generate_slots(
    turf_id: str,
    request: GenerateSlotsRequest,
    current_user: dict = Depends(get_current_owner)
):
    """Generate slots for a date range with progress tracking"""
    db = get_db()
    
    try:
        turf = db.table("turfs") \
            .select("owner_id, price_per_hour") \
            .eq("id", turf_id) \
            .execute()
        
        if not turf.data or len(turf.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turf not found"
            )
        
        if turf.data[0]["owner_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't own this turf"
            )
        
        base_price = turf.data[0]["price_per_hour"]
        slots_generated = []
        slots_skipped = 0
        total_slots = 0
        
        # Parse time strings
        start_time = datetime.strptime(request.start_time, "%H:%M").time()
        end_time = datetime.strptime(request.end_time, "%H:%M").time()
        
        current_date = request.start_date
        while current_date <= request.end_date:
            current_time = datetime.combine(current_date, start_time)
            end_datetime = datetime.combine(current_date, end_time)
            
            while current_time + timedelta(minutes=request.slot_duration) <= end_datetime:
                total_slots += 1
                slot_end = current_time + timedelta(minutes=request.slot_duration)
                
                # Check if slot already exists (duplicate prevention)
                existing = db.table("slots") \
                    .select("id") \
                    .eq("turf_id", turf_id) \
                    .eq("booking_date", current_date.isoformat()) \
                    .eq("start_time", current_time.strftime("%H:%M")) \
                    .execute()
                
                if not existing.data or len(existing.data) == 0:
                    # Check for pricing rules
                    slot_price = base_price
                    
                    pricing_rules = db.table("pricing_rules") \
                        .select("*") \
                        .eq("turf_id", turf_id) \
                        .eq("is_active", True) \
                        .execute()
                    
                    if pricing_rules.data:
                        for rule in pricing_rules.data:
                            day_match = False
                            if rule.get("day_type") == "all":
                                day_match = True
                            elif rule.get("day_type") == "weekday":
                                day_match = current_date.weekday() < 5
                            elif rule.get("day_type") == "weekend":
                                day_match = current_date.weekday() >= 5
                            elif rule.get("day_type") == "custom" and rule.get("custom_date"):
                                custom_date = datetime.strptime(rule["custom_date"], "%Y-%m-%d").date()
                                day_match = current_date == custom_date
                            
                            slot_match = False
                            if rule.get("slot_type") == "all":
                                slot_match = True
                            elif rule.get("slot_type") == "day":
                                slot_match = current_time.hour < 18
                            elif rule.get("slot_type") == "night":
                                slot_match = current_time.hour >= 18
                            
                            time_match = True
                            if rule.get("start_time") and rule.get("end_time"):
                                rule_start = datetime.strptime(rule["start_time"], "%H:%M").time()
                                rule_end = datetime.strptime(rule["end_time"], "%H:%M").time()
                                time_match = rule_start <= current_time <= rule_end
                            
                            if day_match and slot_match and time_match:
                                if rule.get("price") and rule["price"] > 0:
                                    slot_price = rule["price"]
                                break
                    
                    slot = {
                        "turf_id": turf_id,
                        "booking_date": current_date.isoformat(),
                        "start_time": current_time.strftime("%H:%M"),
                        "end_time": slot_end.strftime("%H:%M"),
                        "price": slot_price,
                        "is_booked": False
                    }
                    
                    result = db.table("slots").insert(slot).execute()
                    if result.data and len(result.data) > 0:
                        slots_generated.append(result.data[0])
                else:
                    slots_skipped += 1
                
                current_time = slot_end
            
            current_date += timedelta(days=1)
        
        return {
            "message": f"Generated {len(slots_generated)} slots, skipped {slots_skipped} existing slots",
            "slots": slots_generated,
            "total_generated": len(slots_generated),
            "total_skipped": slots_skipped,
            "total_slots": total_slots,
            "progress": {
                "generated": len(slots_generated),
                "skipped": slots_skipped,
                "total": total_slots,
                "percentage": round((len(slots_generated) / total_slots) * 100 if total_slots > 0 else 0, 2)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating slots: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating slots: {str(e)}"
        )

@router.post("/{turf_id}/pricing-rules")
async def add_pricing_rule(
    turf_id: str,
    rule_data: PricingRuleCreate,
    current_user: dict = Depends(get_current_owner)
):
    """Add a pricing rule for a turf"""
    db = get_db()
    
    try:
        turf = db.table("turfs") \
            .select("owner_id") \
            .eq("id", turf_id) \
            .execute()
        
        if not turf.data or len(turf.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turf not found"
            )
        
        if turf.data[0]["owner_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't own this turf"
            )
        
        # Prepare data - only include fields that are provided
        rule_dict = rule_data.model_dump(exclude_unset=True)
        rule_dict["turf_id"] = turf_id
        rule_dict["is_active"] = True
        
        # Remove day_of_week if day_type is not 'custom'
        if rule_dict.get("day_type") != "custom":
            rule_dict.pop("day_of_week", None)
            rule_dict.pop("custom_date", None)
        
        # Ensure price is set
        if "price" not in rule_dict or rule_dict["price"] is None:
            rule_dict["price"] = 0
        
        logger.info(f"Adding pricing rule: {rule_dict}")
        
        result = db.table("pricing_rules").insert(rule_dict).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add pricing rule"
            )
        
        return {"message": "Pricing rule added successfully", "rule": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding pricing rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add pricing rule: {str(e)}"
        )

# backend/app/api/v1/turfs.py - Add this GET endpoint

@router.get("/{turf_id}/pricing-rules")
async def get_pricing_rules(
    turf_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get pricing rules for a turf"""
    db = get_db()
    
    try:
        # Verify turf exists
        turf = db.table("turfs") \
            .select("id") \
            .eq("id", turf_id) \
            .execute()
        
        if not turf.data or len(turf.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turf not found"
            )
        
        # Get pricing rules
        result = db.table("pricing_rules") \
            .select("*") \
            .eq("turf_id", turf_id) \
            .eq("is_active", True) \
            .execute()
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pricing rules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch pricing rules"
        )

@router.delete("/{turf_id}/pricing-rules/{rule_id}")
async def delete_pricing_rule(
    turf_id: str,
    rule_id: str,
    current_user: dict = Depends(get_current_owner)
):
    """Delete a pricing rule"""
    db = get_db()
    
    try:
        turf = db.table("turfs") \
            .select("owner_id") \
            .eq("id", turf_id) \
            .execute()
        
        if not turf.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turf not found"
            )
        
        if turf.data[0]["owner_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't own this turf"
            )
        
        db.table("pricing_rules") \
            .update({"is_active": False}) \
            .eq("id", rule_id) \
            .eq("turf_id", turf_id) \
            .execute()
        
        return {"message": "Pricing rule deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting pricing rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete pricing rule"
        )