import pytest
from pydantic import ValidationError

from app.cms.schema import WidgetBlock


def w(widget, task="Try it", **config):
    return WidgetBlock(kind="widget", widget=widget, config=config, task=task)


def test_valid_simulations_are_accepted():
    w("sim_linegraph", m0=1, c0=2, goal_m=2, goal_c=-3)
    w("sim_equation", a=2, b=3, c=11)
    w("sim_spinner", parts=6, hit=2)
    w("numberline", task="", start=0)          # existing widgets are unchanged


def test_simulation_needs_a_task():
    with pytest.raises(ValidationError, match="task"):
        w("sim_equation", task="  ", a=2, b=3, c=11)


def test_unknown_or_out_of_range_parameters_are_rejected():
    with pytest.raises(ValidationError, match="no parameter"):
        w("sim_spinner", colour=3)
    with pytest.raises(ValidationError, match="from -5 to 5"):
        w("sim_linegraph", m0=50)
    with pytest.raises(ValidationError):
        w("sim_equation", a="two")


def test_goal_pairs_and_spinner_relation():
    with pytest.raises(ValidationError, match="both goal_m and goal_c"):
        w("sim_linegraph", goal_m=1)
    with pytest.raises(ValidationError, match="smaller than"):
        w("sim_spinner", parts=4, hit=4)


def test_density_simulation_rules():
    w("sim_density", mass0=60, vol0=50, goal="float")
    with pytest.raises(ValidationError, match="one of"):
        w("sim_density", goal="fly")
    with pytest.raises(ValidationError, match="from 1 to 200"):
        w("sim_density", vol0=0)


def test_physics_and_solid_simulations_accept_sensible_settings():
    w("sim_projectile", v0=25, angle0=40, g0=9.8, h0=0, target=50, tol=3)
    w("sim_projectile", v0=25)                                     # no target is fine: free exploration
    w("sim_refraction", n1=1.5, n2=1, angle0=30, goal="tir")
    w("sim_refraction", n1=1, n2=1.5, goal_angle=20)
    w("sim_circuit", volts=9, r1=10, r2=20, mode="parallel", goal_current=1.35)
    w("sim_solid", shape="cone", r=3, h=4, goal_volume=100)
    w("sim_friction", mass0=5, angle0=20, mu0=0.4, goal_angle=30)
    w("sim_optics", element="concave_mirror", f0=10, u0=25, goal="real")
    w("sim_transform", a1=1, a2=1, b1=3, b2=1, c1=1, c2=3, ta1=-1, ta2=1, tb1=-3, tb2=1, tc1=-1, tc2=3)


@pytest.mark.parametrize("widget,config,message", [
    ("sim_projectile", {"v0": 500}, "from 1 to 60"),
    ("sim_projectile", {"target": 50}, "both target and tol"),
    ("sim_projectile", {"g0": 0}, "from 1 to 25"),
    ("sim_refraction", {"n1": 0.5}, "from 1 to 2.5"),
    ("sim_refraction", {"goal": "tir", "goal_angle": 10}, "not both"),
    ("sim_refraction", {"goal": "sink"}, "must be one of"),
    ("sim_circuit", {"mode": "ring"}, "must be one of"),
    ("sim_circuit", {"r1": 0}, "from 1 to 100"),
    ("sim_solid", {"shape": "torus"}, "must be one of"),
    ("sim_solid", {"r": 50}, "from 1 to 10"),
    ("sim_solid", {"colour": 1}, "no parameter"),
    ("sim_transform", {"ta1": 1, "ta2": 2}, "all six target corners"),
    ("sim_friction", {"mu0": 3}, "from 0.05 to 0.9"),
    ("sim_optics", {"element": "prism"}, "must be one of"),
    ("sim_optics", {"goal": "tiny"}, "must be one of"),
    ("sim_transform", {"a1": 20}, "from -8 to 8"),
])
def test_physics_and_solid_simulations_reject_unsafe_settings(widget, config, message):
    with pytest.raises(ValidationError, match=message):
        w(widget, **config)


def test_the_new_simulations_also_need_a_task():
    with pytest.raises(ValidationError, match="task"):
        w("sim_circuit", task="", volts=6)
