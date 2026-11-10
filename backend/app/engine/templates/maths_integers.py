"""Integer templates (Class 6). Level raises the size of the numbers and how often signs mix."""
import random

from app.engine.templates.base import MINUS, Instance, fmt, mcq, register

MIS_SIGN = ("gen-ignores-sign", "Ignores the negative sign and adds or subtracts the sizes only.")
MIS_DIRECTION = ("gen-wrong-direction", "Moves the wrong way on the number line.")


def _span(level: int) -> int:
    return {1: 6, 2: 10, 3: 15, 4: 30, 5: 60}[level]


def _inst(kind_stem, payload, spec, expl, hints, concept, mis):
    return Instance("", 0, 0, 0, "mcq", kind_stem, payload, spec, expl, hints, concept, mis)


class IntAdd:
    id, version, concept = "int_add", 1, "integers-add"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _span(level)
        a, b = rng.randint(1, m), rng.randint(1, m)
        if level >= 2 and rng.random() < 0.7:
            a = -a
        if level >= 3 and rng.random() < 0.6:
            b = -b
        if level == 1 and rng.random() < 0.5:
            b = -min(b, abs(a))
        ans = a + b
        stem = f"What is {fmt(a)} + ({fmt(b)})?" if b < 0 else f"What is {fmt(a)} + {fmt(b)}?"
        wrong = [(fmt(abs(a) + abs(b)), MIS_SIGN), (fmt(a - b), MIS_DIRECTION), (fmt(-ans), MIS_SIGN), (fmt(ans + 1), None), (fmt(ans - 1), None)]
        payload, spec, mis = mcq(fmt(ans), wrong, rng)
        steps = f"{abs(b)} step{'s' if abs(b) != 1 else ''}"
        return _inst(stem, payload, spec, f"Start at {fmt(a)} on the number line and move {steps} {'left' if b < 0 else 'right'}. You land on {fmt(ans)}.",
                     ["Picture the number line. Which way does a negative number move you?", f"Start at {fmt(a)}."], self.concept, mis)


class IntSubtract:
    id, version, concept = "int_subtract", 1, "integers-subtract"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _span(level)
        a = rng.randint(-m if level >= 2 else 0, m)
        b = rng.randint(1, m)
        if level >= 3 and rng.random() < 0.5:
            b = -b
        ans = a - b
        stem = f"What is {fmt(a)} {MINUS} ({fmt(b)})?" if b < 0 else f"What is {fmt(a)} {MINUS} {fmt(b)}?"
        wrong = [(fmt(a + b), ("gen-subtract-as-add", "Adds instead of subtracting, or forgets that subtracting a negative adds.")),
                 (fmt(b - a), ("gen-swaps-order", "Subtracts in the wrong order and loses the sign.")), (fmt(-ans), MIS_SIGN), (fmt(ans + 2), None), (fmt(ans - 2), None), (fmt(ans + 1), None)]
        payload, spec, mis = mcq(fmt(ans), wrong, rng)
        return _inst(stem, payload, spec, f"Subtracting {fmt(b)} is the same as adding {fmt(-b)}. So {fmt(a)} + ({fmt(-b)}) = {fmt(ans)}.",
                     ["Subtracting a number is the same as adding its opposite.", f"The opposite of {fmt(b)} is {fmt(-b)}."], self.concept, mis)


class IntCompare:
    id, version, concept = "int_compare", 1, "integers-compare"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _span(level)
        a, b = rng.sample(range(-m, m + 1), 2)
        ask_small = rng.random() < 0.5
        ans, other = (min(a, b), max(a, b)) if ask_small else (max(a, b), min(a, b))
        stem = f"Which is {'smaller' if ask_small else 'greater'}: {fmt(a)} or {fmt(b)}?"
        payload, spec, mis = mcq(fmt(ans), [(fmt(other), ("gen-bigger-size-bigger-value", "Thinks a number with a bigger size is always greater, even when it is negative.")),
                                            ("They are equal", None), ("Cannot tell", None)], rng)
        return _inst(stem, payload, spec, f"On the number line, numbers to the right are greater. {fmt(ans)} is to the {'left' if ask_small else 'right'} of {fmt(other)}.",
                     ["Place both numbers on a number line.", "The number further to the right is greater."], self.concept, mis)


class IntHops:
    id, version, concept = "int_hops", 1, "integers-number-line"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = max(3, _span(level) // 2)
        start = rng.randint(-m, m)
        hops = rng.randint(2, 3 + level)
        step = rng.randint(1, 2 if level < 3 else 4)
        d = rng.choice([-1, 1])
        end = start + d * hops * step
        stem = f"You start at {fmt(start)} and hop {hops} times, {step} step{'s' if step != 1 else ''} each time, to the {'left' if d < 0 else 'right'}. Where do you land?"
        wrong = [(fmt(start - d * hops * step), MIS_DIRECTION), (fmt(start + d * hops), ("gen-ignores-hop-size", "Counts the hops but not how long each hop is.")), (fmt(abs(end)), MIS_SIGN), (fmt(end + 1), None)]
        payload, spec, mis = mcq(fmt(end), wrong, rng)
        sym = MINUS if d < 0 else "+"
        return _inst(stem, payload, spec, f"{hops} hops of {step} is {hops * step} steps {'left' if d < 0 else 'right'}. {fmt(start)} {sym} {hops * step} = {fmt(end)}.",
                     ["How far do you move in total?", "Left makes the number smaller, right makes it greater."], self.concept, mis)


for _t in (IntAdd(), IntSubtract(), IntCompare(), IntHops()):
    register(_t)
