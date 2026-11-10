"""Content-as-code schema. Authors write YAML; the importer validates it here, then loads it into the database."""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- curriculum / concepts --------------------------------------------------------------------
class BoardDef(Strict):
    id: str
    name: str


class SubjectDef(Strict):
    id: str
    name: str


class VersionDef(Strict):
    board: str
    label: str
    effective_year: int
    verified: bool = False
    note: str = ""


class CurriculumFile(Strict):
    boards: list[BoardDef]
    subjects: list[SubjectDef]
    versions: list[VersionDef]


class Prereq(Strict):
    id: str
    strength: float = Field(1.0, gt=0, le=1)
    why: str = ""


class ConceptDef(Strict):
    id: str
    title: str
    description: str = ""
    grade: int = Field(ge=6, le=10)
    subject: str
    keywords: list[str] = []
    enrichment: bool = False
    prerequisites: list[Prereq] = []


class ConceptsFile(Strict):
    concepts: list[ConceptDef]


# ---- lesson blocks -----------------------------------------------------------------------------
class TextBlock(Strict):
    kind: Literal["text"]
    heading: Optional[str] = None
    html: str


class FigureBlock(Strict):
    kind: Literal["figure"]
    svg: str = ""                    # our own drawing, inline
    asset: Optional[str] = None      # or an approved imported image (source asset id), which must be credited in the lesson's `sources`
    diagram: Optional[dict] = None   # or a diagram spec drawn by ZENITH (see app/services/diagrams.py)
    alt: str = ""
    caption: str = ""

    @model_validator(mode="after")
    def _one_picture(self):
        if self.diagram is not None:
            from app.services.diagrams import DiagramError, render
            if self.svg.strip() or self.asset:
                raise ValueError("a figure with a diagram cannot also have svg or asset")
            try:
                self.svg, auto_alt = render(self.diagram)
            except DiagramError as e:
                raise ValueError(f"diagram: {e}")
            if len(self.alt.strip()) < 8:
                self.alt = auto_alt
            return self
        if not self.alt.strip():
            raise ValueError("a figure needs alt text")
        if bool(self.svg.strip()) == bool(self.asset):
            raise ValueError("a figure needs exactly one of svg or asset")
        return self


# Interactive simulations: allowed parameters and their inclusive bounds. Anything outside is rejected at import.
SIM_BOUNDS: dict[str, dict[str, tuple[float, float]]] = {
    "sim_linegraph": {"m0": (-5, 5), "c0": (-10, 10), "goal_m": (-5, 5), "goal_c": (-10, 10)},
    "sim_equation": {"a": (1, 12), "b": (-20, 20), "c": (-60, 60)},
    "sim_spinner": {"parts": (2, 12), "hit": (1, 11)},
    "sim_density": {"mass0": (1, 500), "vol0": (1, 200)},
}
SIM_CHOICES: dict[str, dict[str, set[str]]] = {"sim_density": {"goal": {"float", "sink"}}}


class WidgetBlock(Strict):
    kind: Literal["widget"]
    widget: Literal["numberline", "balance", "fraction", "sim_linegraph", "sim_equation", "sim_spinner", "sim_density", "data_chart"]
    config: dict[str, Union[int, float, str]] = {}
    task: str = ""

    @model_validator(mode="after")
    def _sim_rules(self):
        if self.widget == "data_chart":
            for k in ("dataset", "x", "y"):
                if not isinstance(self.config.get(k), str) or not str(self.config[k]).strip():
                    raise ValueError(f"data_chart needs '{k}' in config")
            if self.config.get("chart", "line") not in ("line", "bar"):
                raise ValueError("data_chart chart must be line or bar")
            if not self.task.strip():
                raise ValueError("data_chart needs a plain-language task (what to look for or work out).")
            return self
        bounds = SIM_BOUNDS.get(self.widget)
        if bounds is None:
            return self
        if not self.task.strip():
            raise ValueError(f"{self.widget} needs a plain-language task (what the student should try).")
        choices = SIM_CHOICES.get(self.widget, {})
        for k, v in self.config.items():
            if k in choices:
                if v not in choices[k]:
                    raise ValueError(f"{self.widget} parameter '{k}' must be one of: {', '.join(sorted(choices[k]))}.")
                continue
            if k not in bounds:
                raise ValueError(f"{self.widget} has no parameter '{k}'. Allowed: {', '.join([*bounds, *choices])}.")
            lo, hi = bounds[k]
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not lo <= v <= hi:
                raise ValueError(f"{self.widget} parameter '{k}' must be a number from {lo} to {hi}.")
        if self.widget == "sim_linegraph" and ("goal_m" in self.config) != ("goal_c" in self.config):
            raise ValueError("sim_linegraph needs both goal_m and goal_c, or neither.")
        if self.widget == "sim_spinner" and self.config.get("hit", 1) >= self.config.get("parts", 6):
            raise ValueError("sim_spinner 'hit' must be smaller than 'parts'.")
        return self


class ExampleBlock(Strict):
    kind: Literal["example"]
    heading: str = "Worked example"
    prompt: str
    steps: list[str] = Field(min_length=2)


class CalloutBlock(Strict):
    kind: Literal["callout"]
    tone: Literal["watch", "remember", "real"]
    html: str


class CheckBlock(Strict):
    kind: Literal["check"]
    item: str            # item key


class SummaryBlock(Strict):
    kind: Literal["summary"]
    points: list[str] = Field(min_length=1)


Block = Annotated[Union[TextBlock, FigureBlock, WidgetBlock, ExampleBlock, CalloutBlock, CheckBlock, SummaryBlock], Field(discriminator="kind")]


# ---- items -------------------------------------------------------------------------------------
class OptionDef(Strict):
    key: str
    text: str
    misconception: Optional[str] = None     # code of a misconception this wrong option reveals


class ItemConceptRef(Strict):
    id: str
    weight: float = Field(1.0, gt=0, le=1)


class ItemDef(Strict):
    key: str
    kind: Literal["mcq", "multi", "truefalse", "numeric", "fill", "match", "find_error", "label_diagram"]
    stem: str
    purpose: Literal["check", "practice", "test", "probe"] = "practice"
    difficulty: Literal["intro", "standard", "challenge"] = "standard"
    concepts: list[ItemConceptRef] = Field(min_length=1)
    explanation: str
    hints: list[str] = []
    # per kind
    options: list[OptionDef] = []
    correct: Any = None                     # mcq: "B"; multi: ["A","C"]; truefalse: true
    value: Optional[Union[int, float, str]] = None     # numeric
    tolerance: float = 0.0
    unit: Optional[str] = None
    accepted: list[str] = []                # fill
    pairs: dict[str, str] = {}              # match
    diagram: Optional[dict] = None          # label_diagram: a labelled-diagram spec whose shapes carry a numbered `region`
    steps: list[str] = []                   # find_error: a worked solution, one line per step
    wrong_step: Optional[int] = None        # find_error: index of the one wrong line (never 0, the given problem)
    verify: Optional[str] = None            # SymPy expression that must evaluate to the correct numeric answer

    @model_validator(mode="after")
    def _shape(self):
        k = self.kind
        if k in ("mcq", "multi"):
            if len(self.options) < 3:
                raise ValueError("needs at least 3 options")
            keys = [o.key for o in self.options]
            if len(set(keys)) != len(keys):
                raise ValueError("option keys must be unique")
            want = [self.correct] if k == "mcq" else list(self.correct or [])
            if not want or any(w not in keys for w in want):
                raise ValueError("correct answer must be one of the option keys")
        elif k == "truefalse":
            if not isinstance(self.correct, bool):
                raise ValueError("truefalse needs correct: true|false")
        elif k == "numeric":
            if self.value is None:
                raise ValueError("numeric needs value")
        elif k == "fill":
            if not self.accepted:
                raise ValueError("fill needs accepted answers")
        elif k == "match":
            if len(self.pairs) < 3:
                raise ValueError("match needs at least 3 pairs")
        elif k == "label_diagram":
            if self.diagram is None:
                raise ValueError("label_diagram needs a diagram")
            if len(self.pairs) < 3:
                raise ValueError("label_diagram needs at least 3 labelled regions")
            if len(set(self.pairs.values())) != len(self.pairs):
                raise ValueError("label_diagram labels must all be different")
            regions = {str(sh.get("region")) for sh in self.diagram.get("shapes", []) if sh.get("region") is not None}
            if set(self.pairs) != regions:
                raise ValueError(f"label_diagram pairs must match the diagram's numbered regions {sorted(regions)}")
            from app.services.diagrams import DiagramError, render
            try:
                render({**self.diagram, "numbered": True})
            except DiagramError as e:
                raise ValueError(f"diagram: {e}")
        elif k == "find_error":
            if len(self.steps) < 3:
                raise ValueError("find_error needs at least 3 steps")
            if self.wrong_step is None or not 1 <= self.wrong_step < len(self.steps):
                raise ValueError("find_error wrong_step must be a step after the first line")
        return self


class CardDef(Strict):
    key: str
    concept: str
    front: str
    back: str


class MisconceptionDef(Strict):
    code: str
    concept: str
    description: str


class LessonFile(Strict):
    slug: str
    title: str
    minutes: int = Field(ge=3, le=40)
    objectives: list[str] = Field(min_length=1)
    concepts: list[str] = Field(min_length=1)
    origin: Literal["human", "ai_assisted"] = "ai_assisted"
    language: Literal["en", "hi", "te"] = "en"
    blocks: list[Block] = Field(min_length=3)
    sources: list[str] = []          # approved source-asset ids this lesson uses; each is credited to students
    items: list[ItemDef] = []
    cards: list[CardDef] = []
    misconceptions: list[MisconceptionDef] = []

    @model_validator(mode="after")
    def _refs(self):
        keys = {i.key for i in self.items}
        for b in self.blocks:
            if b.kind == "check" and b.item not in keys:
                raise ValueError(f"check block references unknown item '{b.item}'")
        if len(keys) != len(self.items):
            raise ValueError("item keys must be unique within a lesson")
        return self


class ChapterConceptRef(Strict):
    id: str
    role: Literal["core", "foundation"] = "core"


class ChapterFile(Strict):
    slug: str
    board: str
    curriculum: str
    grade: int = Field(ge=6, le=10)
    subject: str
    title: str
    summary: str
    number: Optional[int] = None
    concepts: list[ChapterConceptRef]
    lessons: list[str] = Field(min_length=1)       # lesson slugs, in order
