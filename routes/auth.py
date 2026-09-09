from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from config import supabase

router = APIRouter(prefix="/api/auth", tags=["auth"])

class SignUpSchema(BaseModel):
    email: str
    password: str
    business_name: str
    business_type: str  # e.g., "Plumber", "Mechanic", "Window Cleaner"
    owner_phone: str
    twilio_number: str
    services_offered: str  # e.g., "Oil change ($50), Brake inspection ($30)"
    business_hours: str   # e.g., "Mon-Fri 8am-6pm"
    location_address: str
    faq_notes: Optional[str] = ""

@router.post("/signup")
async def register_business_account(payload: SignUpSchema):
    try:
        # 1. Register user in Supabase Auth
        auth_res = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password
        })
        
        if not auth_res.user:
            raise HTTPException(status_code=400, detail="User registration failed.")

        user_id = auth_res.user.id

        # 2. Insert business profile linked to authenticated user ID
        biz_data = {
            "owner_id": user_id,
            "business_name": payload.business_name,
            "business_type": payload.business_type,
            "owner_phone": payload.owner_phone,
            "twilio_number": payload.twilio_number,
            "services_offered": payload.services_offered,
            "business_hours": payload.business_hours,
            "location_address": payload.location_address,
            "faq_notes": payload.faq_notes
        }
        
        db_res = supabase.table("businesses").insert(biz_data).execute()

        # Return session token so the app keeps them logged in automatically
        return {
            "status": "success",
            "session": auth_res.session,
            "business": db_res.data[0]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
