import os
from typing import Dict, Any

# E2E Test Suite Global Configuration
API_BASE_URL = os.environ.get("E2E_API_BASE_URL", "http://localhost:8000")
API_V1_PREFIX = "/api/v1"

# Groq and AI Provider Configuration
GROQ_API_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_PRIMARY_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK_MODEL = "qwen/qwen3.8-27b"
GROQ_MAX_TOKENS = 1500
GROQ_TIMEOUT_SECONDS = 120.0

LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_MODEL = "google/gemma-4-e4b"

NOMIC_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
NOMIC_EMBEDDING_DIM = 768

# Bayesian Knowledge Tracing (BKT) Canonical Parameters
BKT_PARAMS = {
    "p_l0": 0.25,  # Prior mastery probability
    "p_t": 0.15,   # Probability of learning transition
    "p_g": 0.20,   # Probability of guessing correctly
    "p_s": 0.10,   # Probability of slipping (error despite knowing)
}

# Flagship CBSE Class 10 Math Content Packages
FLAGSHIP_CHAPTERS = [
    "real-numbers",
    "polynomials",
    "linear-equations",
    "quadratic-equations",
]

CHAPTER_NAMES = {
    "real-numbers": "Real Numbers",
    "polynomials": "Polynomials",
    "linear-equations": "Pair of Linear Equations in Two Variables",
    "quadratic-equations": "Quadratic Equations",
}

EXPECTED_RESOURCE_TYPES = [
    "lesson",
    "worked-examples",
    "quick-revision",
    "formula-sheet",
    "practice-set",
]

CORE_BADGES = [
    {"id": "first_steps", "title": "First Steps", "category": "onboarding"},
    {"id": "curious_mind", "title": "Curious Mind", "category": "tutor"},
    {"id": "practice_champion", "title": "Practice Champion", "category": "practice"},
    {"id": "consistency_star", "title": "Consistency Star", "category": "streak"},
    {"id": "concept_master", "title": "Concept Master", "category": "mastery"},
    {"id": "number_wizard", "title": "Number Wizard", "category": "math"},
]

TIMEZONE_STREAKS = "Asia/Kolkata"
SYSTEM_OWNER_ID = "00000000-0000-0000-0000-000000000001"
