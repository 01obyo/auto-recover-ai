from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from config import supabase

router = APIRouter(prefix="/api/auth", tags=["auth"])

class SignUpSchema(BaseModel):
    email: str
    password: str
    business_name: str
    business_type: str
    owner_phone: str
    twilio_number: str
    services_offered: str
    business_hours: str
    location_address: str
    faq_notes: Optional[str] = ""

class OTPRequestSchema(BaseModel):
    email: str

@router.post("/request-otp")
async def request_verification_code(payload: OTPRequestSchema):
    """Sends an OTP code to email/phone with strict rate-limiting (max 3 requests per 15 mins)"""
    try:
        email = payload.email
        
        # 1. Rate Limiting Check in Supabase
        existing_limit = supabase.table("otp_rate_limits").select("*").eq("email", email).execute()
        
        now = datetime.utcnow()
        if existing_limit.data:
            record = existing_limit.data[0]
            last_requested = datetime.fromisoformat(record["last_requested_at"])
            request_count = record["request_count"]
            
            # If within 15 minutes and requests exceed limit
            if now - last_requested < timedelta(minutes=15) and request_count >= 3:
                raise HTTPException(
                    status_code=429, 
                    detail="Too many verification requests. Please wait 15 minutes before trying again."
                )
            
            # Update rate limit counter
            new_count = request_count + 1 if now - last_requested < timedelta(minutes=15) else 1
            supabase.table("otp_rate_limits").update({
                "request_count": new_count,
                "last_requested_at": now.isoformat()
            }).eq("email", email).execute()
        else:
            # First time requesting
            supabase.table("otp_rate_limits").insert({
                "email": email,
                "request_count": 1,
                "last_requested_at": now.isoformat()
            }).execute()

        # 2. Trigger Supabase OTP / Email Verification
        res = supabase.auth.sign_in_with_otp({"email": email})
        return {"status": "success", "message": "Verification code sent successfully."}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/signup")
async def register_business_account(payload: SignUpSchema):
    """Registers account, ensures metadata is saved, and prevents missing records."""
    try:
        # 1. Register user in Supabase Auth
        auth_res = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password
        })
        
        if not auth_res.user:
            raise HTTPException(status_code=400, detail="User registration failed.")

        user_id = auth_res.user.id

        # 2. Check if business profile already exists to prevent duplicates
        existing_biz = supabase.table("businesses").select("id").eq("owner_id", user_id).execute()
        if existing_biz.data:
            return {"status": "success", "message": "Account already exists.", "session": auth_res.session}

        # 3. Insert mandatory business profile metadata
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

        return {
            "status": "success",
            "session": auth_res.session,
            "business": db_res.data[0]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
