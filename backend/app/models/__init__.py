from app.models.base import Base
from app.models.curriculum import CurriculumBoard, Subject, Language, ResourceSource, Resource, ResourceRight
from app.models.learning import LearningPath, PathLesson, LessonVersion, Question, QuizAttempt, ConceptEvidence, ConceptMasterySnapshot, StudyEvent
from app.models.doubts import Doubt, SyncEvent
from app.models.classroom import Classroom, ClassroomMembership, TeacherAction
from app.models.profiles import UserProfile
from app.models.library import (
    Concept,
    ConceptEdge,
    ConceptChapter,
    LibraryEnrollment,
    ResourceProgress,
    ContentRequest,
    LibraryPublicationEvent,
)
from app.models.mastery import BktState, BktEvent
from app.models.rewards import StudentReward, RewardEvent, Badge, StudentBadge
from app.models.diagnostics import DiagnosticSession, DiagnosticItem
from app.models.tutor import TutorThread, TutorMessage

__all__ = [
    "Base",
    "CurriculumBoard",
    "Subject",
    "Language",
    "ResourceSource",
    "Resource",
    "ResourceRight",
    "LearningPath",
    "PathLesson",
    "LessonVersion",
    "Question",
    "QuizAttempt",
    "ConceptEvidence",
    "ConceptMasterySnapshot",
    "StudyEvent",
    "Doubt",
    "SyncEvent",
    "Classroom",
    "ClassroomMembership",
    "TeacherAction",
    "UserProfile",
    # Zenith additions
    "Concept",
    "ConceptEdge",
    "ConceptChapter",
    "LibraryEnrollment",
    "ResourceProgress",
    "ContentRequest",
    "LibraryPublicationEvent",
    "BktState",
    "BktEvent",
    "StudentReward",
    "RewardEvent",
    "Badge",
    "StudentBadge",
    "DiagnosticSession",
    "DiagnosticItem",
    "TutorThread",
    "TutorMessage",
]


