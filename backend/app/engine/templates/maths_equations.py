"""Equation templates (Classes 7-8). Level raises the size of the numbers, the number of steps and the wording."""
import random

from app.engine.templates.base import MINUS, Instance, fmt, mcq, register, sign

MIS_INVERSE = ("gen-wrong-inverse", "Uses the same operation instead of the opposite one, so the number grows instead of disappearing.")
MIS_ONE_SIDE = ("gen-one-side-only", "Changes only one side of the equation.")
MIS_ORDER = ("gen-wrong-order", "Undoes multiplying or dividing before undoing adding or subtracting.")


def _m(level: int) -> int:
    return {1: 9, 2: 15, 3: 25, 4: 40, 5: 60}[level]


def _inst(stem, payload, spec, expl, hints, concept, mis):
    return Instance("", 0, 0, 0, "mcq", stem, payload, spec, expl, hints, concept, mis)


class OneStep:
    id, version, concept = "eq_one_step", 1, "simple-equation-one-step"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _m(level)
        x = rng.randint(-m // 2 if level >= 3 else 1, m) or 1
        kind = rng.choice(["add", "mul"]) if level >= 2 else "add"
        if kind == "add":
            b = rng.randint(1, m)
            if level >= 3 and rng.random() < 0.5:
                b = -b
            rhs = x + b
            stem = f"Solve: x {sign(b)} {abs(b)} = {fmt(rhs)}"
            wrong = [(fmt(rhs + b), MIS_INVERSE), (fmt(b - rhs), ("gen-swaps-sides", "Subtracts in the wrong order.")), (fmt(-x), None), (fmt(x + 1), None)]
            expl = f"Undo {'adding' if b >= 0 else 'subtracting'} {abs(b)} by {'subtracting' if b >= 0 else 'adding'} {abs(b)} on both sides: x = {fmt(rhs)} {MINUS if b >= 0 else '+'} {abs(b)} = {fmt(x)}."
        else:
            a = rng.randint(2, 3 + level)
            rhs = a * x
            stem = f"Solve: {a}x = {fmt(rhs)}"
            wrong = [(fmt(rhs * a), MIS_INVERSE), (fmt(rhs - a), ("gen-subtracts-coefficient", "Subtracts the coefficient instead of dividing by it.")), (fmt(-x), None), (fmt(x + 1), None)]
            expl = f"{a}x means {a} times x. Divide both sides by {a}: x = {fmt(rhs)} ÷ {a} = {fmt(x)}."
        payload, spec, mis = mcq(fmt(x), wrong, rng)
        return _inst(stem, payload, spec, expl, ["Which operation is joined to x? Do the opposite on both sides.", "Check by putting your answer back into the equation."], self.concept, mis)


class TwoStep:
    id, version, concept = "eq_two_step", 1, "simple-equation-two-step"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _m(level)
        a = rng.randint(2, 3 + level)
        x = rng.randint(-m // 3 if level >= 3 else 1, max(2, m // 2)) or 2
        b = rng.randint(1, m)
        if level >= 3 and rng.random() < 0.5:
            b = -b
        rhs = a * x + b
        stem = f"Solve: {a}x {sign(b)} {abs(b)} = {fmt(rhs)}"
        wrong = [(fmt(x + (2 * b) // a if (2 * b) % a == 0 else x + 2), MIS_INVERSE), (fmt(rhs // a - b) if rhs % a == 0 else fmt(x - 2), MIS_ORDER), (fmt(rhs - b), MIS_ONE_SIDE), (fmt(-x), None)]
        payload, spec, mis = mcq(fmt(x), wrong, rng)
        return _inst(stem, payload, spec,
                     f"First undo the {sign(b)} {abs(b)}: {a}x = {fmt(rhs)} {MINUS if b >= 0 else '+'} {abs(b)} = {fmt(a * x)}. Then divide by {a}: x = {fmt(x)}.",
                     ["Undo adding or subtracting first, then multiplying.", f"After undoing the {abs(b)}, what is {a}x equal to?"], self.concept, mis)


class WordProblem:
    id, version, concept = "eq_word", 1, "equation-word-problems"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _m(level)
        price = rng.randint(3, 9 + level * 3)
        n = rng.randint(2, 4 + level)
        extra = rng.randint(2, m)
        total = price * n + extra
        item = rng.choice(["notebooks", "pencils", "sweets", "stickers"])
        stem = f"{n} {item} cost the same each. With a delivery fee of ₹{extra}, the total bill is ₹{total}. How much does one cost (in ₹)?"
        wrong = [(str(price + (2 * extra) // n if (2 * extra) % n == 0 else price + 2), ("gen-adds-fee", "Adds the fee instead of removing it before dividing.")),
                 (str(total // n if total % n == 0 else price - 1), ("gen-ignores-fee", "Divides the whole bill and forgets the fee.")), (str(total - extra), MIS_ONE_SIDE), (str(price + 1), None)]
        payload, spec, mis = mcq(str(price), wrong, rng)
        return _inst(stem, payload, spec, f"Let one cost x. Then {n}x + {extra} = {total}. Subtract {extra}: {n}x = {total - extra}. Divide by {n}: x = {price}.",
                     ["Write the situation as an equation with x for the price of one.", "Remove the fee first."], self.concept, mis)


class BothSides:
    id, version, concept = "eq_both_sides", 1, "linear-eq-both-sides"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _m(level)
        x = rng.randint(-m // 4 if level >= 4 else 1, max(3, m // 3)) or 3
        a = rng.randint(3, 4 + level)
        c = rng.randint(1, a - 1)
        b = rng.randint(-m, m)
        d = a * x + b - c * x                      # a x + b = c x + d has the solution x
        stem = f"Solve: {a}x {sign(b)} {abs(b)} = {c}x {sign(d)} {abs(d)}"
        wrong = [(fmt(x + 1), ("gen-adds-variable-terms", "Adds the x terms instead of moving one across.")), (fmt(x - 1), ("gen-sign-on-transposing", "Moves a term across without changing its sign.")), (fmt(-x), None), (fmt(x + 2), None)]
        payload, spec, mis = mcq(fmt(x), wrong, rng)
        return _inst(stem, payload, spec,
                     f"Take {c}x from both sides: {a - c}x {sign(b)} {abs(b)} = {fmt(d)}. Move the number: {a - c}x = {fmt(d - b)}. So x = {fmt(x)}.",
                     ["Collect the x terms on one side by doing the same thing to both sides.", "Then solve the one-step or two-step equation that is left."], self.concept, mis)


for _t in (OneStep(), TwoStep(), WordProblem(), BothSides()):
    register(_t)
