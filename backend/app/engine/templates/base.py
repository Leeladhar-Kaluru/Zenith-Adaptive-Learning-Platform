"""Question templates: seeded, deterministic, self-checking.

A template turns (seed, level) into one concrete question whose correct answer is computed by code, never by a model.
`generate` refuses any instance whose declared answer is not graded correct by the real grader, so a bad template can
never reach a student.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol

from app.engine import grading

LEVELS = range(1, 6)
MINUS = "−"


class InvalidInstance(ValueError):
    pass


@dataclass
class Instance:
    template_id: str
    version: int
    seed: int
    level: int
    kind: str                      # "mcq"
    stem: str
    payload: dict
    answer_spec: dict
    explanation: str
    hints: list[str]
    concept: str
    misconceptions: dict[str, tuple[str, str]] = field(default_factory=dict)   # option key -> (code, description)


class Template(Protocol):
    id: str
    version: int
    concept: str

    def make(self, rng: random.Random, level: int) -> Instance: ...


REGISTRY: dict[str, Template] = {}


def register(t: Template) -> Template:
    REGISTRY[t.id] = t
    return t


def templates_for(concept: str) -> list[Template]:
    return [t for t in REGISTRY.values() if t.concept == concept]


def _self_check(inst: Instance) -> None:
    if inst.kind != "mcq":
        raise InvalidInstance(f"unsupported kind {inst.kind}")
    keys = [o["key"] for o in inst.payload["options"]]
    texts = [o["text"] for o in inst.payload["options"]]
    if len(set(texts)) != len(texts):
        raise InvalidInstance("duplicate options")
    right = inst.answer_spec["correct"]
    if right not in keys:
        raise InvalidInstance("declared answer is not one of the options")
    if not grading.grade("mcq", inst.answer_spec, {"choice": right}).correct:
        raise InvalidInstance("declared answer not accepted")
    if any(grading.grade("mcq", inst.answer_spec, {"choice": k}).correct for k in keys if k != right):
        raise InvalidInstance("more than one option is correct")


def generate(template_id: str, seed: int, level: int) -> Instance:
    t = REGISTRY[template_id]                      # KeyError for an unknown template
    if level not in LEVELS:
        raise ValueError("level must be 1..5")
    inst = t.make(random.Random(f"{template_id}:{t.version}:{seed}:{level}"), level)
    inst.template_id, inst.version, inst.seed, inst.level = t.id, t.version, seed, level
    _self_check(inst)
    return inst


def fmt(n: int) -> str:
    """Show negatives with a true minus sign."""
    return f"{MINUS}{-n}" if n < 0 else str(n)


def sign(n: int) -> str:
    return "+" if n >= 0 else MINUS


def mcq(correct_text: str, wrong: list[tuple[str, tuple[str, str] | None]], rng: random.Random):
    """Build shuffled A-D options. `wrong` = [(text, (misconception_code, description) | None)]. Duplicates of the correct
    text or of each other are dropped. Returns (payload, answer_spec, {key: misconception})."""
    seen, opts = {correct_text}, [(correct_text, None, True)]
    for text, mis in wrong:
        if text not in seen:
            seen.add(text)
            opts.append((text, mis, False))
    if len(opts) < 3:
        raise InvalidInstance("not enough distinct options")
    opts = opts[:4]
    rng.shuffle(opts)
    keys = "ABCD"
    payload = {"options": [{"key": keys[i], "text": o[0]} for i, o in enumerate(opts)]}
    right = next(keys[i] for i, o in enumerate(opts) if o[2])
    mis = {keys[i]: o[1] for i, o in enumerate(opts) if o[1]}
    return payload, {"correct": right}, mis
