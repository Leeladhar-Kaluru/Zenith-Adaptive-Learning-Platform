"""Which licences ZENITH may import. Anything not listed is refused, so an unrecognised licence can never slip in "for now"."""
from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED = {
    "CC0-1.0": "Public domain dedication.",
    "PDM-1.0": "Public domain mark.",
    "CC-BY-4.0": "Open with credit.",
    "CC-BY-3.0": "Open with credit.",
    "GODL-INDIA": "Government Open Data Licence India: open with credit to the provider, source and licence; no implied endorsement.",
    "US-GOV-PD": "United States government work, generally public domain.",
}
SHARE_ALIKE = {
    "CC-BY-SA-4.0": "Share-alike: show only as a separate, credited item, never merged into lesson text.",
    "CC-BY-SA-3.0": "Share-alike: show only as a separate, credited item, never merged into lesson text.",
    "ODBL-1.0": "Share-alike database licence: use only as a separate, credited dataset.",
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    share_alike: bool
    reason: str


def _norm(licence: str | None) -> str:
    return re.sub(r"[\s_]+", "-", (licence or "").strip()).upper()


def evaluate(licence: str | None) -> Decision:
    key = _norm(licence)
    if not key:
        return Decision(False, False, "No licence was given. An asset without a licence is never imported.")
    if "-NC" in key or key.endswith("NC") or "NONCOMMERCIAL" in key:
        return Decision(False, False, "Non-commercial licences are excluded: ZENITH may be funded commercially later.")
    if "-ND" in key or key.endswith("ND") or "NODERIV" in key:
        return Decision(False, False, "No-derivatives licences are excluded: assets must be allowed to be resized, cropped and adapted.")
    if key in ALLOWED:
        return Decision(True, False, ALLOWED[key])
    if key in SHARE_ALIKE:
        return Decision(True, True, SHARE_ALIKE[key])
    return Decision(False, False, f"The licence '{(licence or '').strip()}' is not on the approved list, so it is refused until a person reviews it.")
