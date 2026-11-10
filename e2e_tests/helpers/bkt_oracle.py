from typing import Tuple, List, Dict, Any
from e2e_tests.test_config import BKT_PARAMS

class BKTOracle:
    """
    Authoritative reference oracle for Bayesian Knowledge Tracing (BKT)
    Equations defined in PROJECT.md and zenith_rebuild_implementation_plan.md:
    p(L0) = 0.25, p(T) = 0.15, p(G) = 0.20, p(S) = 0.10.
    """

    def __init__(
        self,
        p_l0: float = BKT_PARAMS["p_l0"],
        p_t: float = BKT_PARAMS["p_t"],
        p_g: float = BKT_PARAMS["p_g"],
        p_s: float = BKT_PARAMS["p_s"],
    ):
        self.p_l0 = p_l0
        self.p_t = p_t
        self.p_g = p_g
        self.p_s = p_s

    def update(self, prior_p_l: float, correct: bool) -> float:
        """
        Updates knowledge probability p(L) given prior belief and correctness observation.
        """
        prior_p_l = max(0.0001, min(0.9999, prior_p_l))

        if correct:
            numerator = prior_p_l * (1.0 - self.p_s)
            denominator = numerator + (1.0 - prior_p_l) * self.p_g
        else:
            numerator = prior_p_l * self.p_s
            denominator = numerator + (1.0 - prior_p_l) * (1.0 - self.p_g)

        if denominator == 0:
            posterior = prior_p_l
        else:
            posterior = numerator / denominator

        # Transition step: student may have learned during the trial
        p_l_next = posterior + (1.0 - posterior) * self.p_t
        return round(max(0.0001, min(0.9999, p_l_next)), 6)

    def sequence_update(self, initial_p_l: float, observations: List[bool]) -> List[float]:
        """
        Calculates the step-by-step evolution of mastery given a series of observations.
        """
        history = [initial_p_l]
        current = initial_p_l
        for obs in observations:
            current = self.update(current, obs)
            history.append(current)
        return history

    def classify_gap_status(self, errors_count: int, current_p_l: float) -> str:
        """
        Requirement from Section 1 & 4 of Plan:
        - 2+ errors required for a confirmed prerequisite gap
        - 1 error is an "early_signal"
        - 0 errors with high p_l (>= 0.85) is "mastered"
        - else "in_progress"
        """
        if errors_count >= 2:
            return "confirmed_gap"
        elif errors_count == 1:
            return "early_signal"
        elif current_p_l >= 0.85:
            return "mastered"
        return "in_progress"
