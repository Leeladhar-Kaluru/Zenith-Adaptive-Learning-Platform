# ZENITH lesson authoring guide

Read this fully before writing or changing any lesson. Lessons are YAML files in `content/`. They are checked by automated gates, then by a reviewer, and students read them, so accuracy matters more than volume.

## The rules that cannot bend
1. **Original text only.** You may use books and websites to learn what a class covers and how ideas are usually sequenced. Never copy sentences, diagrams, worked examples or questions from NCERT, other textbooks, Canvas Classes, board papers or any website. Write your own explanations, your own numbers and your own questions. Previous-year board papers are copyrighted: never reproduce them. Write NEW questions in the same *pattern*.
2. **Only facts you are certain of.** If you are not sure of a fact, a constant or a formula, leave it out. Check every number you compute. Use SI units and say them.
3. **Product name is ZENITH** (never SETU, never a version suffix). No student names or personal data anywhere.
4. **No links, images from other sites, scripts or iframes** in lesson markup. Diagrams are inline `<svg>` you draw yourself, or one of the built-in simulations.
5. **Reading level:** Flesch-Kincaid grade of the explanation text must be at most (class + 2). Short sentences. Define every new word where it first appears.
6. **Do not import to any database, do not run git, do not edit files you were not given.** You only create or edit the files named in your task, then run the dry-run check.

## Files
- `content/chapters/<grade>-<subject>-<topic>/chapter.yaml` (slug, board `cbse`, curriculum `NCERT current editions (to be confirmed by a reviewer)`, grade, subject `maths` or `science`, title, summary, concepts, lessons list).
- `content/chapters/<chapter>/lessons/<lesson-slug>.yaml`
- New concepts go in your OWN file `content/concepts/<your-task-name>.yaml` with the same format as `content/concepts/science.yaml` (`concepts:` list of `{id, title, grade, subject, description, keywords, prerequisites?}`). Do not edit the shared `maths.yaml` or `science.yaml`.
- Best template to copy: `content/chapters/10-science-light-refraction/lessons/bending-of-light.yaml`. Look at `backend/app/cms/schema.py` for every allowed field and item kind.

## A complete lesson has
- `origin: ai_assisted`, 3 to 4 objectives, `minutes`.
- 3 to 5 `text` blocks with headings; define terms; give a real-life hook first.
- At least one original `figure` (inline SVG with `alt` of 8+ words and a `caption`) and/or a simulation widget. Available widgets and their allowed settings are in `SIM_BOUNDS` in `backend/app/cms/schema.py`: `sim_linegraph`, `sim_equation`, `sim_spinner`, `sim_density`, `sim_projectile`, `sim_refraction`, `sim_circuit`, `sim_solid`, plus `numberline`, `balance`, `fraction`. A widget needs a plain-language `task`. Use a simulation only when it teaches the point.
- At least two `example` blocks, each with 3 or more steps and a check at the end.
- A `callout` with `tone: watch` (common mistake) and one with `tone: real` (everyday use).
- Three inline `check` blocks pointing at items, and a `summary` with 3 or more points.
- **At least 10 items**, covering `intro`, `standard` and `challenge` difficulty, with `purpose` of `check`, `practice` or `test`. Every item: `key` (unique, like `q-xx-1`), `kind`, `stem`, `difficulty`, `purpose`, `concepts: [{id: ...}]`, `explanation` (why the answer is right), `hints` (1 to 2).
  - `mcq`: `correct: B` and 4 `options` with distinct text. Give each WRONG option a `misconception:` code when it reflects a real mistake.
  - `numeric`: `value`, `tolerance: 0.0`, and **`verify:` a SymPy expression that equals the value exactly** (e.g. `verify: 3*4+2`, `verify: (22/7)*7**2*10`). Use whole numbers or exact fractions as answers so the check is exact. Use `asin(1/2)*180/pi` style for angles.
  - Also allowed: `multi`, `truefalse`, `fill`, `match`, `find_error`, `label_diagram` (see schema.py).
- **Board-pattern practice**, written fresh: include at least 2 *assertion and reason* items (an `mcq` whose stem gives "Assertion (A): ... Reason (R): ..." and whose four options are the standard ones: both true and R explains A; both true but R does not explain A; A true, R false; A false, R true) and at least 1 *case-based* item (a short original passage, then an `mcq` about it). Mark them `purpose: test` or `practice`.
- **At least 2 defined misconceptions** in `misconceptions:` (`code`, `concept`, `description`), each used by at least one wrong option. Item options may only use codes defined in that lesson.
- 4 flashcards in `cards:` (`key`, `concept`, `front`, `back`).

## YAML tips
- Put `html:` and long strings in single quotes and double any apostrophe (`Snell''s`), or avoid apostrophes. Quote any string that contains a colon followed by a space.
- In `html`, use only simple tags: `p`, `strong`, `em`, `sub`, `sup`, `ul`, `li`. No inline styles, links or images.
- Do not change the `key` or the wording of existing items when upgrading an existing lesson: only ADD items and blocks. Learners' history is attached to them.

## Check your work (mandatory)
From `backend/`: `.venv/Scripts/python.exe -m app.cms.dryrun ../content <slug> [<slug> ...]` must print PASS for every lesson you wrote, and `.venv/Scripts/python.exe -m app.cli validate ../content` must print OK. Fix every problem it reports. Then re-read your lesson once as a teacher would: is every statement true, every answer key right, every number consistent between text, examples and items?

## Your report back (keep it short)
List the files you created or changed, the dry-run result, and **any statement you are less than fully sure of**, so a reviewer can look at it.
