# ZENITH Pre-Rebuild Database Inventory

**Generated**: 2026-11-06T14:23:24.420688+00:00
**Alembic Head**: `008`

## 1. Table Counts (Public Schema)

| Table Name | Row Count | Status |
| :--- | :--- | :--- |
| `alembic_version` | 1 | Active |
| `classroom_memberships` | 10 | Active |
| `classroom_messages` | 0 | Empty |
| `classrooms` | 10 | Active |
| `coach_notes` | 9 | Active |
| `concept_evidence` | 17 | Active |
| `concept_mastery_snapshots` | 10 | Active |
| `curriculum_boards` | 6 | Active |
| `document_chunks` | 444 | Active |
| `document_pages` | 344 | Active |
| `documents` | 2 | Active |
| `doubts` | 6 | Active |
| `generation_jobs` | 0 | Empty |
| `languages` | 4 | Active |
| `learning_paths` | 6 | Active |
| `lesson_versions` | 66 | Active |
| `path_lessons` | 66 | Active |
| `questions` | 528 | Active |
| `quiz_attempts` | 17 | Active |
| `resource_rights` | 0 | Empty |
| `resource_sources` | 0 | Empty |
| `resources` | 0 | Empty |
| `study_events` | 17 | Active |
| `subjects` | 6 | Active |
| `sync_events` | 0 | Empty |
| `teacher_actions` | 1 | Active |
| `user_profiles` | 8 | Active |

**Total Tables**: 27
**Total Tracked Rows**: 1578

## 2. Integrity & Constraint Checks

- **`lesson_versions (path_lesson_id, version_number)` duplicate count**: 0
  - Result: PASS (0 duplicates)
- **`questions (lesson_version_id, question_key)` duplicate count**: 0
  - Result: PASS (0 duplicates)

## 3. Pre-Rebuild Safety Assessment

- All existing data tables and unique constraints inspected.
- No duplicate composite keys detected in critical learning/question tables.
- Database is safe to apply Alembic migration 009 (Zenith Library, Rewards, and Mastery extensions).
