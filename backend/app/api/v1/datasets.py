import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_profile
from app.models import Profile, SourceAsset

router = APIRouter()


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    """An approved dataset with the credit that must be shown next to it."""
    try:
        a = db.get(SourceAsset, uuid.UUID(dataset_id))
    except ValueError:
        a = None
    if a is None or a.kind not in ("dataset", "geo") or a.status != "approved" or not a.data:
        raise HTTPException(404, "Dataset not found.")
    credit = {"text": a.attribution_text, "url": a.url, "licence": a.licence_id}
    if a.kind == "geo":
        return {"id": str(a.id), "viewBox": a.data["viewBox"], "features": a.data["features"], "credit": credit,
                **{k: a.data[k] for k in ("outline", "note") if a.data.get(k)}}
    return {"id": str(a.id), "fields": a.data["fields"], "rows": a.data["rows"], "credit": credit}
