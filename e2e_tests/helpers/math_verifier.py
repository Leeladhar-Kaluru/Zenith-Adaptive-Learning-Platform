import math
from typing import Tuple, List, Optional

class MathVerifierOracle:
    """
    Mathematical verification oracle verifying equation roots, arithmetic,
    and algebraic identities for CBSE Class 10 items.
    """

    @staticmethod
    def verify_euclid_division(a: int, b: int, q: int, r: int) -> bool:
        """
        Euclid's Division Lemma: a = b*q + r, where 0 <= r < b
        """
        if b <= 0:
            return False
        return (a == b * q + r) and (0 <= r < b)

    @staticmethod
    def verify_hcf_lcm_identity(a: int, b: int, hcf: int, lcm: int) -> bool:
        """
        Fundamental Theorem of Arithmetic identity: HCF(a, b) * LCM(a, b) == a * b
        """
        actual_gcd = math.gcd(a, b)
        actual_lcm = abs(a * b) // actual_gcd
        return (hcf == actual_gcd) and (lcm == actual_lcm) and (hcf * lcm == a * b)

    @staticmethod
    def solve_quadratic_roots(a: float, b: float, c: float) -> Tuple[Optional[float], Optional[float], float]:
        """
        Solves ax^2 + bx + c = 0.
        Returns (root1, root2, discriminant)
        """
        if a == 0:
            raise ValueError("Coefficient 'a' cannot be 0 for quadratic equation")
        disc = b**2 - 4 * a * c
        if disc < 0:
            return None, None, disc
        elif disc == 0:
            r = -b / (2 * a)
            return r, r, disc
        else:
            r1 = (-b + math.sqrt(disc)) / (2 * a)
            r2 = (-b - math.sqrt(disc)) / (2 * a)
            return min(r1, r2), max(r1, r2), disc

    @staticmethod
    def classify_linear_system(
        a1: float, b1: float, c1: float,
        a2: float, b2: float, c2: float
    ) -> str:
        """
        Classifies system of two linear equations:
        a1*x + b1*y + c1 = 0
        a2*x + b2*y + c2 = 0
        Returns: 'unique', 'coincident' (infinitely many), or 'parallel' (no solution)
        """
        det = a1 * b2 - a2 * b1
        if abs(det) > 1e-9:
            return "unique"
        # Check proportional constants
        ratio_a = a1 / a2 if a2 != 0 else None
        ratio_b = b1 / b2 if b2 != 0 else None
        ratio_c = c1 / c2 if c2 != 0 else None
        
        # Parallel if a1/a2 == b1/b2 != c1/c2
        if (ratio_c is not None and ratio_a is not None and abs(ratio_a - ratio_c) > 1e-9):
            return "parallel"
        return "coincident"
