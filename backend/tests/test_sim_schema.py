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
