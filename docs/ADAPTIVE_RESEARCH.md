# Adaptive learning: what to add, and why (research notes)

Written from the established literature, not invented claims. Each item says what we already have, what to add, and how it stays deterministic and auditable (AGENTS rule 7).

| Idea | Evidence base | We have | Add |
|---|---|---|---|
| **Knowledge tracing** (probability a skill is known, updated per answer) | Bayesian Knowledge Tracing, Corbett and Anderson 1995 | BKT per concept (`engine/bkt.py`) | Guess/slip tuned per item from data; show the probability and its evidence to the student |
| **Elo / Rasch for item difficulty and learner ability** | Elo in education, Pelanek 2016; Rasch 1960 | Learner theta per subject, item beta (`engine/elo.py`) | Uncertainty (number of observations) so new items move fast and old ones slowly |
| **Target the right difficulty** | The "85 % rule" of optimal learning, Wilson et al. 2019; zone of proximal development | Selector prefers items near theta | Choose items with predicted success 70 to 85 %, and say so ("a little hard on purpose") |
| **Computerised adaptive testing with early stopping** | IRT-based CAT, Wainer et al. | Fixed-length tests | Adaptive test: pick the most informative next item, stop when the ability estimate's confidence interval is narrow enough; report the interval honestly |
| **Spaced repetition and forgetting** | Ebbinghaus 1885; SM-2; FSRS-style memory models | Revision schedule | Decay mastery with time since last evidence; schedule review when predicted recall falls below a threshold |
| **Response time and hints** | Response-time models, van der Linden 2006 | Hints used and ms stored | Treat a fast correct answer as stronger evidence than a slow one with hints; flag rapid guessing (very fast and wrong) as low-quality evidence |
| **Misconception-targeted remediation** | Diagnostic questions research (Wylie, Wiliam) | Tagged misconceptions, gap engine | After a repeated wrong-option pattern, give a short repair set built from items that expose that exact misconception |
| **Prerequisite-aware sequencing** | Knowledge space theory, Doignon and Falmagne | Concept graph with edges | Walk back along the graph to the weakest prerequisite before pushing forward |
| **Interleaving and retrieval practice** | Rohrer and Taylor 2007; Roediger and Karpicke 2006 | Mixed practice by pattern | Mix topics inside a session once each is above a threshold |
| **Calibration and confidence** | Metacognition research | None | Optional "how sure are you?" tap; compare with correctness and show calibration over time |
| **Offline-safe adaptation** | Product requirement | Offline queue, idempotent sync | Keep a small local model snapshot so the next question can adapt offline; reconcile on sync |

## Build order (matches PLAN_NEXT.md)
1. Evidence weighting by response time, hints and guess detection (small, pure, tested).
2. Mastery decay and review scheduling by predicted recall.
3. Adaptive test with early stopping and a reported interval.
4. Misconception repair sets.
5. Target-difficulty explanation shown to the student.
6. Confidence tap and calibration chart (opt in).

## Transparency
Every adaptation stores: the model version, the inputs (evidence ids), and a plain-language reason. The student sees the reason; the teacher sees the same data.
