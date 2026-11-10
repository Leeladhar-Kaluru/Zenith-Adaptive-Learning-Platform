"""Science templates: density and floating (Class 6), pressure (Class 8). Level raises the numbers and the reasoning steps."""
import random

from app.engine.templates.base import Instance, mcq, register


def _inst(stem, payload, spec, expl, hints, concept, mis):
    return Instance("", 0, 0, 0, "mcq", stem, payload, spec, expl, hints, concept, mis)


def _fmt(x: float) -> str:
    return f"{x:g}"


def _whole(rate: float, base: float) -> tuple[float, int]:
    """Return (base, rate * base) with the product a whole number, doubling the base until it is (e.g. 2.7 per unit needs 10 units)."""
    for k in (1, 2, 4, 5, 10, 20):
        prod = round(rate * base * k, 6)
        if prod == int(prod):
            return base * k, int(prod)
    return base * 10, int(round(rate * base * 10))


class DensityCalc:
    id, version, concept = "density_calc", 1, "float-sink"

    def make(self, rng: random.Random, level: int) -> Instance:
        vol = rng.choice([10, 20, 25, 40, 50, 80] if level <= 2 else [12, 15, 30, 60, 75, 120])
        d = rng.choice([1, 2, 3, 4, 5, 8]) if level <= 3 else rng.choice([0.5, 1.5, 2.5, 7.5, 0.8, 2.7])
        vol, mass = _whole(d, vol)
        wrong = [(_fmt(mass * vol), ("gen-multiplies-mass-volume", "Multiplies mass and volume instead of dividing mass by volume.")), (_fmt(vol / mass), ("gen-divides-volume-by-mass", "Divides volume by mass, the wrong way round.")),
                 (_fmt(mass - vol), None), (_fmt(d + 1), None)]
        payload, spec, mis = mcq(_fmt(d), wrong, rng)
        return _inst(f"An object has a mass of {mass} g and a volume of {vol} cm³. What is its density in g/cm³?", payload, spec,
                     f"Density = mass divided by volume = {mass} divided by {vol} = {_fmt(d)} g/cm³.", ["Density = mass divided by volume."], self.concept, mis)


class FloatDecision:
    id, version, concept = "float_decision", 1, "float-sink"

    def make(self, rng: random.Random, level: int) -> Instance:
        liquid, ld = rng.choice([("water", 1.0), ("water", 1.0), ("oil", 0.8), ("salt water", 1.2)]) if level >= 3 else ("water", 1.0)
        d = round(rng.choice([0.2, 0.4, 0.6, 0.7, 0.9, 1.1, 1.5, 2.0, 2.7, 3.0, 7.8]), 1)
        if abs(d - ld) < 0.05:
            d += 0.5
        floats = d < ld
        right = "It floats" if floats else "It sinks"
        wrong = [("It sinks" if floats else "It floats", ("gen-heavy-sinks" if floats else "gen-small-floats", "Decides from how heavy or large the object seems instead of comparing densities.")), ("It hovers in the middle", None), ("It dissolves", None)]
        payload, spec, mis = mcq(right, wrong, rng)
        return _inst(f"An object has a density of {_fmt(d)} g/cm³. The liquid is {liquid}, with a density of {_fmt(ld)} g/cm³. What happens to the object?", payload, spec,
                     f"The object's density ({_fmt(d)}) is {'less' if floats else 'more'} than the density of {liquid} ({_fmt(ld)}), so it {'floats' if floats else 'sinks'}.",
                     ["Compare the object's density with the liquid's density."], self.concept, mis)


class PressureCalc:
    id, version, concept = "pressure_calc", 1, "pressure-force-area"

    def make(self, rng: random.Random, level: int) -> Instance:
        area = rng.choice([2, 4, 5, 10] if level <= 2 else [0.5, 2.5, 4, 8, 20])
        p = rng.choice([10, 20, 50, 100] if level <= 3 else [15, 120, 250, 400, 1200])
        area, force = _whole(p, area)
        wrong = [(_fmt(force * area), ("gen-multiplies-force-area", "Multiplies force and area instead of dividing force by area.")), (_fmt(area / force), ("gen-divides-area-by-force", "Divides area by force, the wrong way round.")),
                 (_fmt(force - area), None), (_fmt(p + 10), None)]
        payload, spec, mis = mcq(_fmt(p), wrong, rng)
        return _inst(f"A force of {force} N acts on an area of {_fmt(area)} m². What is the pressure in Pa?", payload, spec,
                     f"Pressure = force divided by area = {force} divided by {_fmt(area)} = {_fmt(p)} Pa.", ["Pressure = force divided by area."], self.concept, mis)


for _t in (DensityCalc(), FloatDecision(), PressureCalc()):
    register(_t)
