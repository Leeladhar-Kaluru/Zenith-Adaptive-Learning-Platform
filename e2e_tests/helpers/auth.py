import uuid
import re
from typing import Dict, Optional

UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

def is_valid_uuid(val: str) -> bool:
    if not isinstance(val, str):
        return False
    try:
        uuid_obj = uuid.UUID(val)
        return str(uuid_obj).lower() == val.lower()
    except (ValueError, AttributeError):
        return False

def create_test_student_headers(student_id: Optional[str] = None) -> Dict[str, str]:
    uid = student_id or str(uuid.uuid4())
    return {
        "X-User-Id": uid,
        "X-Role": "student",
        "Content-Type": "application/json",
        "Authorization": f"Bearer mock_student_token_{uid}",
    }

def create_test_teacher_headers(teacher_id: Optional[str] = None) -> Dict[str, str]:
    uid = teacher_id or str(uuid.uuid4())
    return {
        "X-User-Id": uid,
        "X-Role": "teacher",
        "Content-Type": "application/json",
        "Authorization": f"Bearer mock_teacher_token_{uid}",
    }

def create_anonymous_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
    }

def generate_idempotency_key(prefix: str = "attempt") -> str:
    return f"{prefix}:{uuid.uuid4()}"
