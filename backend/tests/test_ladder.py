from app.engine import ladder, signals


def run(seq, level=1, **kw):
    up = down = 0
    reasons = []
    for correct in seq:
        level, up, down, why = ladder.step(level, up, down, correct=correct, **kw)
        reasons.append(why)
    return level, reasons


def test_two_clean_correct_raise_level():
    assert run([True, True])[0] == 2


def test_one_correct_does_not():
    assert run([True])[0] == 1


def test_hinted_correct_is_neutral_and_keeps_streak():
    lvl, up, down, why = ladder.step(2, 1, 0, correct=True, hints_used=1)
    assert (lvl, up, down) == (2, 1, 0) and why


def test_two_wrong_lower_one_wrong_does_not():
    assert run([False, False], level=3)[0] == 2
    assert run([False], level=3)[0] == 3


def test_struggling_single_wrong_lowers():
    lvl, *_ = ladder.step(3, 0, 0, correct=False, struggling=True)
    assert lvl == 2


def test_fluent_single_correct_raises():
    lvl, *_ = ladder.step(2, 0, 0, correct=True, fluent=True)
    assert lvl == 3


def test_guessing_never_raises():
    lvl, up, _, _ = ladder.step(2, 1, 0, correct=True, guessing=True)
    assert lvl == 2 and up == 0


def test_bounds_and_reasons():
    assert run([True] * 30)[0] == 5
    assert run([False] * 30, level=5)[0] == 1
    assert all(r for r in run([True, False, True, True, False, False])[1])


def test_wrong_resets_up_streak():
    assert run([True, False, True])[0] == 1


def test_signals_guessing_fluent_struggling():
    ev = []
    assert signals.classify(ev, ms=500, correct=False, median_ms=10000)["guessing"]
    s = signals.classify(ev, ms=500, correct=True, median_ms=10000)
    assert not s["guessing"] and not s["fluent"]            # too fast even when right: not counted as fluent
    assert signals.classify(ev, ms=6000, correct=True, median_ms=10000)["fluent"]
    assert not signals.classify([{"kind": "hint_open"}], ms=6000, correct=True, median_ms=10000)["fluent"]
    assert signals.classify([{"kind": "hint_open"}, {"kind": "hint_open"}], ms=20000, correct=False, median_ms=10000)["struggling"]
    assert signals.classify([], ms=1000, correct=True, median_ms=0)["reason"]
