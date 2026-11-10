"""Deterministic Keyword/BM25 Curriculum Retrieval Service for SETU.

Retrieves relevant curriculum content snippets (reading blocks, definitions,
and worked examples) from CBSE Class 10 Mathematics packages to ground the Socratic Tutor.
Pure python scoring without external vector database dependencies (Requirement 4).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

LIBRARY_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "content",
    "library",
)
CONTENT_DIR = os.path.join(LIBRARY_BASE_DIR, "cbse-10-math")


@dataclass
class CurriculumSnippet:
    index: int
    block_id: str
    source_title: str
    heading: str
    text: str
    concept_id: str = ""
    score: float = 0.0


def _tokenize(text: str) -> List[str]:
    """Basic alphanumeric word tokenizer with stopword stripping."""
    words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "of", "and", "or",
        "to", "in", "for", "with", "on", "at", "by", "from", "up", "about",
        "into", "over", "after", "how", "what", "why", "when", "where", "which",
        "can", "you", "tell", "me", "please", "find", "solve", "give", "answer",
    }
    return [w for w in words if w not in stopwords and len(w) > 1]


def retrieve_curriculum_context(
    query: str,
    chapter_slug: Optional[str] = None,
    resource_key: Optional[str] = None,
    concept_id: Optional[str] = None,
    max_snippets: int = 3,
) -> Tuple[str, Dict[int, CurriculumSnippet]]:
    """Retrieves top matching curriculum content blocks and formats numbered context.
    
    Returns:
        (formatted_context_string, dict_of_snippets_by_index)
    """
    clean_slug = chapter_slug or ""
    for pfx in ["cbse-10-math-", "cbse-06-math-", "cbse-07-math-", "cbse-08-math-", "cbse-09-math-", "cbse-10-science-"]:
        clean_slug = clean_slug.replace(pfx, "")

    query_tokens = set(_tokenize(query))
    query_phrase = query.lower().strip()

    candidate_snippets: List[CurriculumSnippet] = []

    # Collect candidate files across all curriculum folders
    candidate_files = []
    if os.path.exists(LIBRARY_BASE_DIR):
        for root, _, files in os.walk(LIBRARY_BASE_DIR):
            for fname in files:
                if fname.endswith(".json") and fname != "manifest.json" and not fname.endswith("-diag.json"):
                    if clean_slug and clean_slug not in fname and clean_slug not in root:
                        continue
                    candidate_files.append(os.path.join(root, fname))

    if not candidate_files:
        return "No curriculum reference documents available.", {}

    for file_path in candidate_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        fname = os.path.basename(file_path)

        source_title = data.get("title", fname.replace(".json", "").replace("-", " ").title())

        # 1. Search Reading Blocks
        for b in data.get("blocks", []):
            b_id = b.get("id", "blk")
            heading = b.get("heading", "")
            content = b.get("content", "")
            full_text = f"{heading}\n{content}"

            block_tokens = _tokenize(full_text)
            overlap = len(query_tokens & set(block_tokens))

            # Phrase match scoring
            phrase_bonus = 10.0 if (query_phrase and len(query_phrase) > 5 and query_phrase in full_text.lower()) else 0.0
            heading_bonus = 5.0 * len(query_tokens & set(_tokenize(heading)))
            concept_bonus = 3.0 if (concept_id and concept_id in b.get("conceptIds", [])) else 0.0

            score = (overlap * 1.5) + phrase_bonus + heading_bonus + concept_bonus
            if score > 0.5:
                candidate_snippets.append(
                    CurriculumSnippet(
                        index=0,
                        block_id=b_id,
                        source_title=source_title,
                        heading=heading or "Curriculum Reading",
                        text=content[:400],
                        score=score,
                    )
                )

        # 2. Search Worked Examples
        for we in data.get("workedExamples", []):
            we_id = we.get("id", "we")
            problem = we.get("problem", "")
            steps = " ".join(we.get("steps", []))
            answer = str(we.get("answer", ""))
            full_text = f"{problem}\n{steps}\n{answer}"

            we_tokens = _tokenize(full_text)
            overlap = len(query_tokens & set(we_tokens))

            phrase_bonus = 10.0 if (query_phrase and len(query_phrase) > 5 and query_phrase in full_text.lower()) else 0.0
            score = (overlap * 1.5) + phrase_bonus
            if score > 0.5:
                candidate_snippets.append(
                    CurriculumSnippet(
                        index=0,
                        block_id=we_id,
                        source_title=source_title,
                        heading=f"Worked Example: {problem[:50]}...",
                        text=f"Problem: {problem}\nSteps: {steps}\nAnswer: {answer}"[:400],
                        score=score,
                    )
                )

    if not candidate_snippets:
        # Fallback snippet from manifest if search yielded no hits
        return "No specific curriculum snippets matched the query.", {}

    # Sort descending by score
    candidate_snippets.sort(key=lambda s: s.score, reverse=True)
    top_snippets = candidate_snippets[:max_snippets]

    # Assign 1-based index
    formatted_parts = []
    snippet_map: Dict[int, CurriculumSnippet] = {}

    for idx, snippet in enumerate(top_snippets, start=1):
        snippet.index = idx
        snippet_map[idx] = snippet
        formatted_parts.append(
            f"[{idx}] {snippet.source_title} | {snippet.heading} ({snippet.block_id})\n{snippet.text}"
        )

    formatted_context = "\n\n".join(formatted_parts)
    return formatted_context, snippet_map
