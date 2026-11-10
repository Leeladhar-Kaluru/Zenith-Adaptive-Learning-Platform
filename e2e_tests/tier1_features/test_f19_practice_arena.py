import os
import re
import pytest

def _get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr:
        if os.path.isdir(os.path.join(curr, "frontend", "src")):
            return curr
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return os.path.abspath(".")

PROJECT_ROOT = _get_project_root()
FRONTEND_SRC = os.path.join(PROJECT_ROOT, "frontend", "src")
PRACTICE_PAGE_TSX = os.path.join(FRONTEND_SRC, "pages", "PracticePage.tsx")
PRACTICE_MODULE_CSS = os.path.join(FRONTEND_SRC, "pages", "PracticePage.module.css")


def _read_practice_files():
    assert os.path.isfile(PRACTICE_PAGE_TSX), f"Missing {PRACTICE_PAGE_TSX}"
    assert os.path.isfile(PRACTICE_MODULE_CSS), f"Missing {PRACTICE_MODULE_CSS}"
    with open(PRACTICE_PAGE_TSX, "r", encoding="utf-8") as f:
        tsx_content = f.read()
    with open(PRACTICE_MODULE_CSS, "r", encoding="utf-8") as f:
        css_content = f.read()
    return tsx_content, css_content


def test_practice_session_setup(student_client):
    """Feature 19: Starting a practice session delivers calibrated questions with student redaction."""
    tsx_content, _ = _read_practice_files()

    # 1. Verify frontend page initializes session via api client
    assert "api.createPracticeSession" in tsx_content or "api.startDiagnosticSession" in tsx_content
    assert "const [questions, setQuestions] = useState" in tsx_content
    assert "const [currentIndex, setCurrentIndex] = useState(0)" in tsx_content

    # 2. Test live backend endpoint delivering questions
    res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    assert res.status_code == 201
    items = res.json()["items"]
    assert len(items) >= 6

    # 3. Invariant: student payloads must be redacted (zero leak of answerKey or teacher explanations)
    for item in items:
        assert "answer_key" not in item
        assert "answerKey" not in item
        assert "explanation" not in item
        assert "options" in item
        assert "question" in item or "prompt" in item
        assert len(item["options"]) >= 2


def test_interactive_answer_submission(student_client):
    """Feature 19: Submitting answer invokes api.submitPracticeAttempt and receives immediate scoring."""
    tsx_content, _ = _read_practice_files()

    # 1. Verify frontend invokes api.submitPracticeAttempt with the full contract payload
    assert "api.submitPracticeAttempt" in tsx_content
    assert "questionId: currentQ.questionId" in tsx_content
    assert "conceptId: currentQ.conceptId" in tsx_content
    assert "response: selectedOption" in tsx_content
    assert "hintLevel:" in tsx_content
    assert "hintsUsed:" in tsx_content
    assert "syncIdempotencyKey: idempotencyKey" in tsx_content
    assert "setSubmitResult(res)" in tsx_content

    # 2. Verify idempotency key format embeds question ID and timestamp
    assert re.search(r"practice_\$\{currentQ\.questionId\}_\$\{Date\.now\(\)\}", tsx_content)

    # 3. Test live backend submission contract
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    assert session_res.status_code == 201
    session_id = session_res.json()["session_id"]

    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [{"item_id": "real-numbers-d1", "student_response": "A", "is_correct": True}]
    })
    assert submit_res.status_code == 200
    assert submit_res.json()["correct_items"] == 1
    assert "score" in submit_res.json()
    assert "mastery_probability" in submit_res.json()


def test_scratchpad_state_isolation():
    """Feature 19: Scratchpad state remains strictly client-isolated from network payloads."""
    tsx_content, css_content = _read_practice_files()

    # 1. State hooks in PracticePage.tsx
    assert "const [showScratchpad, setShowScratchpad] = useState(false)" in tsx_content
    assert "const [scratchNotes, setScratchNotes] = useState('')" in tsx_content

    # 2. Toggle button with Edit3 icon
    assert "onClick={() => setShowScratchpad(!showScratchpad)}" in tsx_content
    assert "<Edit3" in tsx_content

    # 3. Textarea rendering with controlled value and change handler
    assert "<textarea" in tsx_content
    assert "className={styles.scratchpadTextarea}" in tsx_content
    assert "value={scratchNotes}" in tsx_content
    assert "onChange={(e) => setScratchNotes(e.target.value)}" in tsx_content
    assert "placeholder=\"Rough calculations & scratchpad notes (stays on your screen during the quiz)…\"" in tsx_content

    # 4. Strict isolation: scratchNotes must NEVER be transmitted in network payloads
    submit_attempt_block = tsx_content[tsx_content.find("api.submitPracticeAttempt"):tsx_content.find("api.submitPracticeAttempt") + 500]
    assert "scratchNotes" not in submit_attempt_block
    assert "showScratchpad" not in submit_attempt_block

    submit_diag_block = tsx_content[tsx_content.find("api.submitDiagnostic"):tsx_content.find("api.submitDiagnostic") + 500]
    assert "scratchNotes" not in submit_diag_block

    offline_queue_block = tsx_content[tsx_content.find("queuePracticeAttemptOffline"):tsx_content.find("queuePracticeAttemptOffline") + 500]
    assert "scratchNotes" not in offline_queue_block

    # 5. CSS module definitions
    assert ".scratchpad {" in css_content
    assert ".scratchpadTextarea {" in css_content


def test_xp_toast_payload(student_client):
    """Feature 19: Practice completion triggers XP award toast event and genuine KaTeX math rendering."""
    tsx_content, css_content = _read_practice_files()

    # 1. XP Toast animation markup and CSS in PracticePage.tsx
    assert "styles.xpToast" in tsx_content
    assert "<Zap size={14} />" in tsx_content
    assert "+{submitResult.rewards.xpAwarded} XP" in tsx_content
    assert ".xpToast {" in css_content

    # 2. KaTeX typography integration in Practice Arena
    assert "import { Button, Badge, Progress, MathText, Callout } from '../components/ui'" in tsx_content
    assert "<MathText content={currentQ.prompt} />" in tsx_content
    assert "<MathText content={currentQ.hints[0]} />" in tsx_content
    assert "<MathText content={opt} />" in tsx_content
    assert "<MathText content={submitResult.explanation} />" in tsx_content

    # 3. Live backend daily claim / XP rewards event
    res = student_client.post("/api/v1/rewards/claim-daily", headers={"Idempotency-Key": "toast-test-f19"})
    assert res.status_code == 200
    assert res.json()["xp_awarded"] > 0


def test_quiz_completion_summary(student_client):
    """Feature 19: Completion summary provides score, BKT mastery change, and recommendations."""
    tsx_content, _ = _read_practice_files()

    # 1. Verify hint penalty tracking in frontend
    assert "const [hintsUsed, setHintsUsed] = useState(0)" in tsx_content
    assert "const [showHint, setShowHint] = useState(false)" in tsx_content
    assert "setHintsUsed((prev) => prev + 1)" in tsx_content
    assert "setShowHint(true)" in tsx_content
    assert "Hint ({hintsUsed})" in tsx_content

    # Reset upon moving to next question
    next_question_block = tsx_content[tsx_content.find("const handleNext"):tsx_content.find("const handleNext") + 600]
    assert "setShowHint(false)" in next_question_block
    assert "setHintsUsed(0)" in next_question_block

    # 2. Verify summary card UI rendering
    assert "styles.summaryCard" in tsx_content
    assert "Assessment Summary" in tsx_content
    assert "{diagSummary.accuracyPct}%" in tsx_content
    assert "diagSummary.recommendedPractice" in tsx_content

    # 3. Verify error handling and offline queue fallback
    assert "queuePracticeAttemptOffline" in tsx_content
    assert "Answer saved offline! Evaluation and knowledge tracing will sync upon reconnection." in tsx_content
    assert "masteryBand: 'queued'" in tsx_content

    # 4. Live backend summary evaluation contract
    session_res = student_client.post("/api/v1/diagnostics/session", json_data={"chapter_slug": "real-numbers"})
    assert session_res.status_code == 201
    session_id = session_res.json()["session_id"]

    submit_res = student_client.post("/api/v1/diagnostics/submit", json_data={
        "session_id": session_id,
        "responses": [
            {"item_id": "real-numbers-d1", "student_response": "A", "is_correct": True},
            {"item_id": "real-numbers-d2", "student_response": "B", "is_correct": False},
        ]
    })
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert "score" in data
    assert "mastery_probability" in data
    assert "recommended_practice" in data
