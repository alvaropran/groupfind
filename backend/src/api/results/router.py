from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.database import SessionLocal
from src.models.activity import ActivityModel
from src.models.message import ExtractedMessageModel

router = APIRouter()


@router.get("/{job_id}")
async def get_results(job_id: str) -> dict:
    """Get extracted activities with reviews and booking links."""
    db = SessionLocal()
    try:
        activities = (
            db.query(ActivityModel)
            .filter(ActivityModel.job_id == UUID(job_id))
            .order_by(ActivityModel.review_rating.desc().nullslast())
            .all()
        )

        if not activities:
            raise HTTPException(status_code=404, detail="No activities found")

        message_count = (
            db.query(ExtractedMessageModel)
            .filter(ExtractedMessageModel.job_id == UUID(job_id))
            .count()
        )

        destination = activities[0].destination if activities else ""

        activity_list = [
            {
                "id": str(a.id),
                "name": a.name,
                "type": a.activity_type,
                "area": a.area,
                "destination": a.destination,
                "who_suggested": a.who_suggested,
                "what_they_said": a.what_they_said,
                "details": a.details,
                "review": {
                    "rating": float(a.review_rating) if a.review_rating else None,
                    "summary": a.review_summary,
                    "pros": a.review_pros or [],
                    "cons": a.review_cons or [],
                    "best_tip": a.review_best_tip,
                    "sources": a.review_sources or [],
                } if a.review_rating else None,
                "booking_options": a.booking_options or [],
            }
            for a in activities
        ]

        return {
            "destination": destination,
            "activities": activity_list,
            "message_count": message_count,
        }
    finally:
        db.close()
