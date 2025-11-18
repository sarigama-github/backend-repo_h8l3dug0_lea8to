"""
Database Schemas for Discover Portugal

Each Pydantic model represents a collection in MongoDB. The collection name is
the lowercase of the class name.

- Event -> "event"
- Rsvp -> "rsvp"
- User -> "user"
"""
from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, List
from datetime import datetime

class Location(BaseModel):
    name: Optional[str] = Field(None, description="Venue or place name")
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")

class Event(BaseModel):
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    category: str = Field(..., description="Event category (Culture, Outdoors, Food, etc.)")
    start_time: datetime = Field(..., description="Start date/time in ISO format")
    end_time: Optional[datetime] = Field(None, description="End date/time in ISO format")
    location: Location = Field(..., description="Location info including coordinates")
    image_url: Optional[HttpUrl] = Field(None, description="Cover image URL")
    organizer_name: str = Field(..., description="Organizer display name")
    organizer_email: EmailStr = Field(..., description="Organizer contact email")

class Rsvp(BaseModel):
    event_id: str = Field(..., description="Referenced event _id as string")
    user_name: str = Field(..., description="Attendee name")
    user_email: EmailStr = Field(..., description="Attendee email")
    status: str = Field("going", description="RSVP status: going, interested, cancelled")

class User(BaseModel):
    name: str
    email: EmailStr
    bio: Optional[str] = None
    interests: Optional[List[str]] = None
    is_active: bool = True
