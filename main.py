import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Event as EventSchema, Rsvp as RsvpSchema

app = FastAPI(title="Discover Portugal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utils
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

def serialize_doc(doc):
    if not doc:
        return doc
    d = dict(doc)
    if d.get("_id"):
        d["_id"] = str(d["_id"]) 
    # Convert datetimes to isoformat
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        # nested location stays as-is
    return d

@app.get("/")
def read_root():
    return {"message": "Discover Portugal API is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Olá from Discover Portugal backend!"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Configured"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Event Endpoints
@app.post("/api/events")
def create_event(event: EventSchema):
    try:
        inserted_id = create_document("event", event)
        return {"_id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/events")
def list_events(category: Optional[str] = None, city: Optional[str] = None, q: Optional[str] = None, limit: int = Query(50, ge=1, le=200)):
    filter_q = {}
    if category:
        filter_q["category"] = category
    if city:
        filter_q["location.city"] = city
    # Simple text search on title/description (non-indexed)
    if q:
        filter_q["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}}
        ]
    try:
        docs = get_documents("event", filter_q, limit=limit)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/events/{event_id}")
def get_event(event_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        doc = db["event"].find_one({"_id": ObjectId(event_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Event not found")
        return serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# RSVP Endpoints
@app.post("/api/rsvps")
def create_rsvp(rsvp: RsvpSchema):
    try:
        inserted_id = create_document("rsvp", rsvp)
        return {"_id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/rsvps")
def list_rsvps(user_email: Optional[str] = None, event_id: Optional[str] = None, limit: int = Query(100, ge=1, le=300)):
    filter_q = {}
    if user_email:
        filter_q["user_email"] = user_email
    if event_id:
        filter_q["event_id"] = event_id
    try:
        docs = get_documents("rsvp", filter_q, limit=limit)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/my")
def my_overview(email: str = Query(..., description="User email to filter created and RSVP'd events")):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        created = list(db["event"].find({"organizer_email": email}).limit(100))
        rsvps = list(db["rsvp"].find({"user_email": email}).limit(200))
        # hydrate RSVP with event
        events_by_id = {}
        event_ids = [ObjectId(r["event_id"]) for r in rsvps if ObjectId.is_valid(r.get("event_id", ""))]
        if event_ids:
            for ev in db["event"].find({"_id": {"$in": event_ids}}):
                events_by_id[str(ev["_id"])] = serialize_doc(ev)
        hydrated_rsvps = []
        for r in rsvps:
            rd = serialize_doc(r)
            ev = events_by_id.get(r.get("event_id"))
            rd["event"] = ev
            hydrated_rsvps.append(rd)
        return {
            "created_events": [serialize_doc(c) for c in created],
            "rsvps": hydrated_rsvps
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
