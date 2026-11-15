from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date, time, datetime

# ============================================================================
# Authentication & User Models
# ============================================================================
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, example="Alex Rivera")
    email: str = Field(..., min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", example="alex.rivera@student.edu")
    password: str = Field(..., min_length=6, example="studentpassword123")
    phone: Optional[str] = Field(None, max_length=20, example="+1-555-0101")
    role: Optional[str] = Field("member", pattern="^(admin|member)$")

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", example="alex.rivera@student.edu")
    password: str = Field(..., example="studentpassword123")

class UserSummary(BaseModel):
    user_id: int
    library_card_no: str
    full_name: str
    email: str
    role: str
    status: str
    phone: Optional[str] = None
    created_at: Optional[Any] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary

# ============================================================================
# Book & Catalog Models
# ============================================================================
class BookCreateRequest(BaseModel):
    isbn: str = Field(..., min_length=10, max_length=20, example="978-0132350884")
    title: str = Field(..., min_length=2, max_length=255, example="Clean Architecture")
    subtitle: Optional[str] = Field(None, max_length=255, example="A Craftsman's Guide")
    publisher_name: Optional[str] = Field(None, example="Prentice Hall")
    category_id: int = Field(..., example=2)
    publication_year: Optional[int] = Field(None, ge=1800, le=2100, example=2017)
    edition: Optional[str] = Field("1st Edition", example="1st Edition")
    language: Optional[str] = Field("English", example="English")
    pages: Optional[int] = Field(None, gt=0, example=432)
    description: Optional[str] = Field(None, example="Universal rules of software structure and architecture.")
    cover_image_url: Optional[str] = Field(None, example="https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&q=80")
    authors: List[str] = Field(..., min_items=1, example=["Robert C. Martin"])

class AddCopyRequest(BaseModel):
    barcode: str = Field(..., min_length=3, max_length=50, example="BC-2001")
    shelf_location: str = Field(..., min_length=2, max_length=80, example="Aisle 2, Shelf B-3")
    condition: Optional[str] = Field("new", pattern="^(new|good|damaged)$")

# ============================================================================
# Loan & Circulation Models
# ============================================================================
class IssueLoanRequest(BaseModel):
    library_card_no: str = Field(..., example="LIB-STU-101")
    barcode: str = Field(..., example="BC-1001")
    due_days: Optional[int] = Field(14, ge=1, le=90, description="Loan duration in days")

class ReturnLoanByBarcodeRequest(BaseModel):
    barcode: str = Field(..., example="BC-1001")

# ============================================================================
# Waitlist Models
# ============================================================================
class JoinWaitlistRequest(BaseModel):
    book_id: int = Field(..., example=1)

# ============================================================================
# Study Room Models
# ============================================================================
class BookRoomRequest(BaseModel):
    room_id: int = Field(..., example=1)
    booking_date: date = Field(..., example="2026-11-18")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}(:\d{2})?$", example="10:00:00")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}(:\d{2})?$", example="12:00:00")

# ============================================================================
# Book Acquisition Request Models
# ============================================================================
class CreateAcquisitionRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, example="System Design Interview")
    author: str = Field(..., min_length=2, max_length=150, example="Alex Xu")
    isbn: Optional[str] = Field(None, max_length=20, example="978-1736049112")
    estimated_price: Optional[float] = Field(None, ge=0.0, example=39.99)

class UpdateRequestStatus(BaseModel):
    status: str = Field(..., pattern="^(open|approved|purchased)$")
