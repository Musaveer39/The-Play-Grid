# backend/app/api/v1/bookings.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import logging

from app.core.database import get_db
from app.core.security import get_current_user, get_current_owner

logger = logging.getLogger(__name__)
router = APIRouter()

# =============== SCHEMAS ===============

class BookingCreate(BaseModel):
    turf_id: str
    slot_ids: List[str]
    booking_date: date
    start_time: str
    end_time: str
    total_amount: float
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    booking_type: str = "online"

class BookingResponse(BaseModel):
    id: str
    user_id: str
    turf_id: str
    slot_ids: List[str]
    booking_date: str
    start_time: str
    end_time: str
    total_amount: float
    status: str
    booking_type: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    created_at: str
    turf: Optional[dict] = None
    slots: Optional[List[dict]] = None

class BookingUpdateStatus(BaseModel):
    status: str

# =============== ENDPOINTS ===============

@router.get("/", response_model=List[BookingResponse])
async def get_user_bookings(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get user's bookings"""
    db = get_db()
    
    try:
        query = db.table("bookings") \
            .select("*, turf:turfs(*)") \
            .eq("user_id", current_user["id"])
        
        if status:
            query = query.eq("status", status)
        
        query = query.order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        
        bookings = []
        for booking in result.data:
            if isinstance(booking.get("booking_date"), date):
                booking["booking_date"] = booking["booking_date"].isoformat()
            if isinstance(booking.get("created_at"), datetime):
                booking["created_at"] = booking["created_at"].isoformat()
            bookings.append(booking)
        
        return bookings
        
    except Exception as e:
        logger.error(f"Error fetching bookings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching bookings"
        )

@router.post("/", response_model=BookingResponse)
async def create_booking(
    booking_data: BookingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new booking with multiple slots"""
    db = get_db()
    
    try:
        # Verify all slots exist and are available
        available_slots = []
        for slot_id in booking_data.slot_ids:
            slot = db.table("slots") \
                .select("*") \
                .eq("id", slot_id) \
                .eq("is_booked", False) \
                .execute()
            
            if not slot.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Slot {slot_id} is already booked or unavailable"
                )
            available_slots.append(slot.data[0])
        
        # Verify turf exists
        turf = db.table("turfs") \
            .select("*") \
            .eq("id", booking_data.turf_id) \
            .eq("is_active", True) \
            .execute()
        
        if not turf.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turf not found"
            )
        
        # Create booking
        booking_dict = {
            "user_id": current_user["id"],
            "turf_id": booking_data.turf_id,
            "slot_ids": booking_data.slot_ids,
            "booking_date": booking_data.booking_date.isoformat(),
            "start_time": booking_data.start_time,
            "end_time": booking_data.end_time,
            "total_amount": booking_data.total_amount,
            "status": "pending",
            "booking_type": booking_data.booking_type,
            "customer_name": booking_data.customer_name or current_user.get("full_name"),
            "customer_phone": booking_data.customer_phone or current_user.get("phone")
        }
        
        result = db.table("bookings").insert(booking_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create booking"
            )
        
        booking = result.data[0]
        
        # Update all slots as booked
        for slot in available_slots:
            db.table("slots") \
                .update({"is_booked": True, "booking_id": booking["id"]}) \
                .eq("id", slot["id"]) \
                .execute()
        
        booking["turf"] = turf.data[0]
        booking["slots"] = available_slots
        
        # Serialize dates
        if isinstance(booking.get("booking_date"), date):
            booking["booking_date"] = booking["booking_date"].isoformat()
        if isinstance(booking.get("created_at"), datetime):
            booking["created_at"] = booking["created_at"].isoformat()
        
        return booking
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating booking: {str(e)}"
        )

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get booking details"""
    db = get_db()
    
    try:
        result = db.table("bookings") \
            .select("*, turf:turfs(*)") \
            .eq("id", booking_id) \
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        booking = result.data[0]
        
        # Check permission
        if booking["user_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this booking"
            )
        
        # Serialize dates
        if isinstance(booking.get("booking_date"), date):
            booking["booking_date"] = booking["booking_date"].isoformat()
        if isinstance(booking.get("created_at"), datetime):
            booking["created_at"] = booking["created_at"].isoformat()
        
        return booking
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching booking"
        )

@router.put("/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status_data: BookingUpdateStatus,
    current_user: dict = Depends(get_current_user)
):
    """Update booking status"""
    db = get_db()
    
    try:
        booking = db.table("bookings") \
            .select("*, turf:turfs(*)") \
            .eq("id", booking_id) \
            .execute()
        
        if not booking.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        booking = booking.data[0]
        
        # Check permission
        if current_user["role"] != "admin":
            turf = db.table("turfs") \
                .select("owner_id") \
                .eq("id", booking["turf_id"]) \
                .execute()
            
            if not turf.data or turf.data[0]["owner_id"] != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to update this booking"
                )
        
        # Update status
        result = db.table("bookings") \
            .update({"status": status_data.status}) \
            .eq("id", booking_id) \
            .execute()
        
        # If cancelled, free up the slot
        if status_data.status == "cancelled":
            for slot_id in booking.get("slot_ids", []):
                db.table("slots") \
                    .update({"is_booked": False, "booking_id": None}) \
                    .eq("id", slot_id) \
                    .execute()
        
        return {"message": "Booking status updated", "status": status_data.status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating booking"
        )