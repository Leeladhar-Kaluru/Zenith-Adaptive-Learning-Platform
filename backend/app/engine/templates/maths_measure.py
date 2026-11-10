"""Templates for fractions, area and perimeter, squares and roots. Level raises the size of the numbers and the number of steps."""
import random

from app.engine.templates.base import Instance, mcq, register


def _inst(stem, payload, spec, expl, hints, concept, mis):
    return Instance("", 0, 0, 0, "mcq", stem, payload, spec, expl, hints, concept, mis)


def _span(level: int) -> int:
    return {1: 9, 2: 14, 3: 25, 4: 40, 5: 90}[level]


class AreaRect:
    id, version, concept = "area_rect", 1, "area-perimeter-rect"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _span(level)
        a, b = rng.randint(2, m), rng.randint(2, m)
        unit = rng.choice(["cm", "m"])
        wrong = [(f"{2 * (a + b)} square {unit}", ("gen-perimeter-for-area", "Adds the sides (perimeter) when the question asks for the space inside (area).")), (f"{a + b} square {unit}", ("gen-adds-two-sides", "Adds length and width instead of multiplying.")),
                 (f"{a * b + a} square {unit}", None), (f"{a * b - b} square {unit}", None)]
        payload, spec, mis = mcq(f"{a * b} square {unit}", wrong, rng)
        return _inst(f"A rectangle is {a} {unit} long and {b} {unit} wide. What is its area?", payload, spec, f"Area = length times width = {a} times {b} = {a * b} square {unit}.",
                     ["Area is the space inside. Multiply the two sides."], self.concept, mis)


class PerimeterRect:
    id, version, concept = "perimeter_rect", 1, "area-perimeter-rect"

    def make(self, rng: random.Random, level: int) -> Instance:
        m = _span(level)
        a, b = rng.randint(2, m), rng.randint(2, m)
        unit = rng.choice(["cm", "m"])
        wrong = [(f"{a * b} {unit}", ("gen-area-for-perimeter", "Multiplies the sides (area) when the question asks for the distance around (perimeter).")), (f"{a + b} {unit}", ("gen-adds-two-sides-only", "Adds only the length and the width, not all four sides.")),
                 (f"{2 * a + b} {unit}", None), (f"{2 * (a + b) + 2} {unit}", None)]
        payload, spec, mis = mcq(f"{2 * (a + b)} {unit}", wrong, rng)
        return _inst(f"A rectangle is {a} {unit} long and {b} {unit} wide. What is its perimeter?", payload, spec, f"Perimeter = {a} + {b} + {a} + {b} = {2 * (a + b)} {unit}.",
                     ["Perimeter is the distance around. A rectangle has four sides."], self.concept, mis)


class SquareOf:
    id, version, concept = "square_of", 1, "squares-roots"

    def make(self, rng: random.Random, level: int) -> Instance:
        n = rng.randint(2, {1: 9, 2: 12, 3: 15, 4: 25, 5: 40}[level])
        wrong = [(str(2 * n), ("gen-doubles-instead-of-squares", "Multiplies the number by 2 instead of by itself.")), (str(n * (n + 1)), None), (str(n * n - n), None), (str(n * n + 2 * n), None)]
        payload, spec, mis = mcq(str(n * n), wrong, rng)
        return _inst(f"What is {n} squared?", payload, spec, f"{n} squared is {n} times {n} = {n * n}.", ["Multiply the number by itself."], self.concept, mis)


class SquareRoot:
    id, version, concept = "square_root", 1, "squares-roots"

    def make(self, rng: random.Random, level: int) -> Instance:
        n = rng.randint(2, {1: 9, 2: 12, 3: 15, 4: 25, 5: 40}[level])
        wrong = [(str(n * n // 2 if (n * n) % 2 == 0 else n + 1), ("gen-halves-instead-of-root", "Divides the number by 2 instead of finding the number that multiplies by itself.")), (str(n + 1), None), (str(n - 1), None), (str(n * 2), None)]
        payload, spec, mis = mcq(str(n), wrong, rng)
        return _inst(f"What is the square root of {n * n}?", payload, spec, f"{n} times {n} is {n * n}, so the square root of {n * n} is {n}.", ["Which number multiplied by itself gives this number?"], self.concept, mis)


class FracCompare:
    id, version, concept = "frac_compare", 1, "fractions-compare"

    def make(self, rng: random.Random, level: int) -> Instance:
        d = rng.randint(3, 6 + 2 * level)
        same_den = level <= 2 or rng.random() < 0.5
        if same_den:
            a, b = rng.sample(range(1, d), 2) if d > 2 else (1, 2)
            f1, f2 = f"{a}/{d}", f"{b}/{d}"
            big, small = (f1, f2) if a > b else (f2, f1)
            expl = f"Both have the denominator {d}, so the pieces are the same size. {max(a, b)} pieces is more than {min(a, b)} pieces, so {big} is greater."
        else:
            n = rng.randint(1, 4)
            d1, d2 = rng.sample(range(n + 1, n + 3 + 2 * level), 2)
            f1, f2 = f"{n}/{d1}", f"{n}/{d2}"
            big, small = (f1, f2) if d1 < d2 else (f2, f1)
            expl = f"Both have the numerator {n}. The bigger denominator means smaller pieces, so {big} is greater."
        ask_greater = rng.random() < 0.5
        right, other = (big, small) if ask_greater else (small, big)
        wrong = [(other, ("gen-bigger-bottom-bigger-fraction", "Thinks a bigger denominator makes a bigger fraction.") if not same_den else ("gen-compares-wrong-part", "Compares the wrong numbers.")), ("They are equal", None), ("Cannot tell", None)]
        payload, spec, mis = mcq(right, wrong, rng)
        return _inst(f"Which is {'greater' if ask_greater else 'smaller'}: {f1} or {f2}?", payload, spec, expl.replace("is greater", "is greater" if ask_greater else "is greater, so the other is smaller"),
                     ["Look at the numerators and the denominators. Which one is the same?"], self.concept, mis)


for _t in (AreaRect(), PerimeterRect(), SquareOf(), SquareRoot(), FracCompare()):
    register(_t)
