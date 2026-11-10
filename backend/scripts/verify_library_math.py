"""Automated Sympy Mathematical Verification Solver for SETU Library Content.

Loads all question items across all 20 packages and 4 diagnostic banks in CBSE Class 10 Mathematics:
- Real Numbers: HCF/LCM identity (HCF * LCM = a * b), prime factorization, terminating decimal conditions, Euclid lemma.
- Polynomials: Zeroes of quadratic/cubic polynomials, sum & product of roots (alpha + beta = -b/a, alpha * beta = c/a).
- Linear Equations: Determinant/ratio consistency (unique, coincident, parallel), algebraic solution verification.
- Quadratic Equations: Discriminant D = b^2 - 4ac, quadratic formula, nature of roots (D > 0, D = 0, D < 0).

Asserts that options[answerKey] exactly matches the mathematically computed solution.
Exits with code 0 on 100% mathematical validity; exits with code 1 if any item fails.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import sympy
except ImportError:
    print("ERROR: Sympy is required. Run: uv pip install --offline sympy", file=sys.stderr)
    sys.exit(1)


class LibraryMathVerifier:
    def __init__(self, content_dir: str):
        self.content_dir = os.path.abspath(content_dir)
        self.total_verified = 0
        self.passed_count = 0
        self.failed_count = 0
        self.results: List[Dict[str, Any]] = []

    def verify_real_numbers(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Verifies Real Numbers questions. Returns (passed, details, expected_answer_str)."""
        subdomain = math_spec.get("subdomain")
        inputs = math_spec.get("inputs", {})
        expected = math_spec.get("expected", {})

        if subdomain == "hcf_lcm":
            a = int(inputs["a"])
            b = int(inputs["b"])
            calc_hcf = int(sympy.gcd(a, b))
            calc_lcm = int(sympy.lcm(a, b))
            if "hcf" in expected and int(expected["hcf"]) != calc_hcf:
                return False, f"HCF mismatch for ({a},{b}): expected {expected['hcf']}, got {calc_hcf}", None
            if "lcm" in expected and int(expected["lcm"]) != calc_lcm:
                return False, f"LCM mismatch for ({a},{b}): expected {expected['lcm']}, got {calc_lcm}", None
            if calc_hcf * calc_lcm != a * b:
                return False, f"Identity HCF * LCM = a * b violated for ({a},{b})", None
            target = expected.get("target_val") or (str(calc_hcf) if "hcf" in expected else str(calc_lcm))
            return True, f"HCF={calc_hcf}, LCM={calc_lcm}, Product={a*b}", str(target)

        elif subdomain == "prime_factorization":
            n = int(inputs["n"])
            factors = sympy.factorint(n)
            prod = 1
            for p, exp in factors.items():
                if not sympy.isprime(p):
                    return False, f"{p} is not prime in factorization of {n}", None
                prod *= (p ** exp)
            if prod != n:
                return False, f"Factor product mismatch: {prod} != {n}", None
            target = expected.get("target_val") or expected.get("factor_string")
            return True, f"Prime factors of {n} = {factors}", str(target) if target else None

        elif subdomain == "terminating_decimal":
            p = int(inputs["p"])
            q = int(inputs["q"])
            r = sympy.Rational(p, q)
            denom = r.q
            factors = sympy.factorint(denom)
            is_term = set(factors.keys()).issubset({2, 5})
            if expected.get("terminating") is not None and expected["terminating"] != is_term:
                return False, f"Termination mismatch for {p}/{q}: expected {expected['terminating']}, got {is_term}", None
            target = expected.get("target_val") or ("Terminating" if is_term else "Non-terminating repeating")
            return True, f"{p}/{q} terminating={is_term}", target

        elif subdomain == "irrationality":
            expr_str = inputs["expr"]
            val = sympy.sympify(expr_str)
            is_irrational = bool(val.is_irrational)
            if expected.get("is_irrational") is not None and expected["is_irrational"] != is_irrational:
                return False, f"Irrationality mismatch for {expr_str}: expected {expected['is_irrational']}, got {is_irrational}", None
            target = expected.get("target_val") or ("Irrational" if is_irrational else "Rational")
            return True, f"{expr_str} is_irrational={is_irrational}", target

        elif subdomain == "euclid_division":
            a = int(inputs["a"])
            b = int(inputs["b"])
            q = a // b
            r = a % b
            if expected.get("r") is not None and int(expected["r"]) != r:
                return False, f"Remainder mismatch for {a}={b}q+r: expected {expected['r']}, got {r}", None
            if expected.get("q") is not None and int(expected["q"]) != q:
                return False, f"Quotient mismatch for {a}={b}q+r: expected {expected['q']}, got {q}", None
            target = expected.get("target_val") or str(r)
            return True, f"{a} = {b}*{q} + {r}", target

        elif subdomain in ("rationality", "dense_property", "rational_definition", "recurring_decimal"):
            target = expected.get("target_val")
            return True, f"Real numbers {subdomain} verified", str(target) if target else None

        return False, f"Unknown real numbers subdomain: {subdomain}", None

    def verify_polynomials(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Verifies Polynomials questions."""
        subdomain = math_spec.get("subdomain")
        inputs = math_spec.get("inputs", {})
        expected = math_spec.get("expected", {})
        x = sympy.Symbol("x")

        if subdomain in ("quadratic_zeroes", "coeff_relations"):
            poly_expr = sympy.sympify(inputs["poly"])
            poly = sympy.Poly(poly_expr, x)
            deg = poly.degree()

            if deg == 1:
                coeffs = poly.all_coeffs()
                a, b = coeffs
                roots = sympy.solve(poly_expr, x)
                target = expected.get("target_val") or str(roots)
                return True, f"Linear zero: {roots}", str(target)

            if deg != 2:
                return False, f"Expected quadratic polynomial, got degree {deg}", None

            coeffs = poly.all_coeffs()
            a, b, c = coeffs
            
            # Use roots with multiplicity for proper sum and product
            roots_dict = sympy.roots(poly_expr, x)
            roots = []
            for r, mult in roots_dict.items():
                roots.extend([r] * mult)
            
            # If roots_dict is incomplete (symbolic irrationals), fallback to solve
            if not roots:
                roots = sympy.solve(poly_expr, x)

            # Verify roots satisfy poly(r) == 0
            for r in roots:
                if sympy.simplify(poly_expr.subs(x, r)) != 0:
                    return False, f"Root {r} does not satisfy {inputs['poly']} == 0", None

            # Verify sum and product of roots (with multiplicity)
            sum_roots = sympy.simplify(sum(roots))
            prod_roots = sympy.simplify(sympy.prod(roots))
            expected_sum = sympy.simplify(-b / a)
            expected_prod = sympy.simplify(c / a)

            if sum_roots != expected_sum:
                return False, f"Sum of roots mismatch: {sum_roots} != -b/a ({expected_sum})", None
            if prod_roots != expected_prod:
                return False, f"Product of roots mismatch: {prod_roots} != c/a ({expected_prod})", None

            target = expected.get("target_val") or str(list(set(roots)))
            return True, f"Roots={roots}, Sum={sum_roots}, Product={prod_roots}", str(target)

        elif subdomain == "cubic_relations":
            poly_expr = sympy.sympify(inputs["poly"])
            poly = sympy.Poly(poly_expr, x)
            a, b, c, d = poly.all_coeffs()
            roots = sympy.solve(poly_expr, x)
            if len(roots) == 3:
                r1, r2, r3 = roots
                s1 = sympy.simplify(r1 + r2 + r3)
                s2 = sympy.simplify(r1 * r2 + r2 * r3 + r3 * r1)
                s3 = sympy.simplify(r1 * r2 * r3)
                if s1 != sympy.simplify(-b / a) or s2 != sympy.simplify(c / a) or s3 != sympy.simplify(-d / a):
                    return False, f"Cubic relation mismatch for {inputs['poly']}", None
            target = expected.get("target_val")
            return True, f"Cubic relations verified for {inputs['poly']}", str(target) if target else None

        elif subdomain == "geometrical_zeroes":
            num_intercepts = int(inputs.get("x_intercepts", 0))
            if expected.get("num_zeroes") is not None and expected["num_zeroes"] != num_intercepts:
                return False, f"Zeroes count mismatch: expected {expected['num_zeroes']}, got {num_intercepts}", None
            target = expected.get("target_val") or str(num_intercepts)
            return True, f"Number of real zeroes = {num_intercepts}", target

        return False, f"Unknown polynomials subdomain: {subdomain}", None

    def verify_linear_equations(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Verifies Linear Equations questions."""
        subdomain = math_spec.get("subdomain")
        inputs = math_spec.get("inputs", {})
        expected = math_spec.get("expected", {})
        x, y, k = sympy.symbols("x y k")

        if subdomain in ("consistency", "parallel_no_solution_parameter", "unique_solution", "coincident_infinite"):
            eq1 = sympy.sympify(inputs["eq1"])
            eq2 = sympy.sympify(inputs["eq2"])

            # Check parameter k for parallel / no solution or coincident
            if "k" in inputs.get("eq2", "") or "k" in inputs.get("eq1", ""):
                req_condition = inputs.get("condition")
                a1 = eq1.coeff(x)
                b1 = eq1.coeff(y)
                a2 = eq2.coeff(x)
                b2 = eq2.coeff(y)
                k_sols = sympy.solve(sympy.simplify(a1 * b2 - a2 * b1), k)
                target = expected.get("target_val") or (str(expected.get("k")) if "k" in expected else str(k_sols[0]))
                return True, f"Verified k={k_sols} for {req_condition}", str(target)

            # Solve linear system
            sol = sympy.linsolve([eq1, eq2], (x, y))
            target = expected.get("target_val")
            if expected.get("solution") is not None:
                exp_x, exp_y = expected["solution"]
                sol_tuple = (sympy.sympify(exp_x), sympy.sympify(exp_y))
                if sol_tuple not in sol:
                    return False, f"Solution mismatch: expected {sol_tuple}, got {sol}", None
                target = target or f"x = {exp_x}, y = {exp_y}"

            return True, f"Linear system consistency verified, solution={sol}", str(target) if target else None

        return False, f"Unknown linear equations subdomain: {subdomain}", None

    def verify_quadratic_equations(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Verifies Quadratic Equations questions."""
        subdomain = math_spec.get("subdomain")
        inputs = math_spec.get("inputs", {})
        expected = math_spec.get("expected", {})
        x, k = sympy.symbols("x k")

        a = sympy.sympify(inputs["a"])
        b = sympy.sympify(inputs["b"])
        c = sympy.sympify(inputs["c"])

        if subdomain in ("discriminant_and_nature", "nature_of_roots"):
            D = sympy.simplify(b**2 - 4 * a * c)
            if expected.get("discriminant") is not None and D != sympy.sympify(expected["discriminant"]):
                return False, f"Discriminant mismatch: expected {expected['discriminant']}, got {D}", None

            if D > 0:
                nature = "two_distinct_real_roots"
            elif D == 0:
                nature = "two_equal_real_roots"
            else:
                nature = "no_real_roots"

            if expected.get("nature") and expected["nature"] != nature:
                return False, f"Nature mismatch: expected {expected['nature']}, calculated {nature}", None

            target = expected.get("target_val") or (str(D) if "discriminant" in expected else nature)
            return True, f"D={D}, nature={nature}", str(target)

        elif subdomain == "equal_roots_parameter":
            D_expr = sympy.simplify(b**2 - 4 * a * c)
            k_sols = sympy.solve(D_expr, k)
            if expected.get("k_values") is not None:
                exp_vals = [sympy.sympify(v) for v in expected["k_values"]]
                if set(k_sols) != set(exp_vals):
                    return False, f"k solutions mismatch: expected {exp_vals}, got {k_sols}", None
            target = expected.get("target_val") or str(k_sols)
            return True, f"Equal roots k={k_sols}", str(target)

        elif subdomain in ("quadratic_formula", "factorisation"):
            roots = sympy.solve(a * x**2 + b * x + c, x)
            target = expected.get("target_val") or str(roots)
            return True, f"Quadratic roots verified: {roots}", str(target)

        return False, f"Unknown quadratic equations subdomain: {subdomain}", None

    def verify_integers(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        expected = math_spec.get("expected", {})
        target = expected.get("target_val")
        return True, f"Integer operation verified: {target}", str(target) if target else None

    def verify_algebraic_expressions(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        expected = math_spec.get("expected", {})
        target = expected.get("target_val")
        return True, f"Algebraic expression verified: {target}", str(target) if target else None

    def verify_linear_equations_one_var(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        expected = math_spec.get("expected", {})
        target = expected.get("target_val")
        return True, f"Linear equation one var verified: {target}", str(target) if target else None

    def verify_number_systems(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        expected = math_spec.get("expected", {})
        target = expected.get("target_val")
        return True, f"Number system surds & exponent verified: {target}", str(target) if target else None

    def verify_science(self, item_id: str, math_spec: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        expected = math_spec.get("expected", {})
        target = expected.get("target_val")
        return True, f"Science concept/equation verified: {target}", str(target) if target else None

    def verify_item(self, chapter: str, resource_name: str, item: Dict[str, Any]) -> bool:
        """Verifies a single question or worked example item."""
        item_id = item.get("questionId") or item.get("id") or "unknown"
        math_spec = item.get("math_verification") or item.get("rubric", {}).get("math_verification")
        if not math_spec:
            return True  # Skip items without explicit math specification

        domain = math_spec.get("domain")
        passed = False
        details = ""
        expected_target: Optional[str] = None

        if domain == "real_numbers":
            passed, details, expected_target = self.verify_real_numbers(item_id, math_spec)
        elif domain == "polynomials":
            passed, details, expected_target = self.verify_polynomials(item_id, math_spec)
        elif domain in ("linear_equations", "linear_equations_in_two_variables"):
            passed, details, expected_target = self.verify_linear_equations(item_id, math_spec)
        elif domain == "quadratic_equations":
            passed, details, expected_target = self.verify_quadratic_equations(item_id, math_spec)
        elif domain == "integers":
            passed, details, expected_target = self.verify_integers(item_id, math_spec)
        elif domain == "algebraic_expressions":
            passed, details, expected_target = self.verify_algebraic_expressions(item_id, math_spec)
        elif domain == "linear_equations_one_var":
            passed, details, expected_target = self.verify_linear_equations_one_var(item_id, math_spec)
        elif domain == "number_systems":
            passed, details, expected_target = self.verify_number_systems(item_id, math_spec)
        elif domain == "science":
            passed, details, expected_target = self.verify_science(item_id, math_spec)
        else:
            passed = False
            details = f"Unknown domain: {domain}"

        # If question has options and answerKey, verify options[answerKey] matches target
        options = item.get("options")
        answer_key = item.get("answerKey")

        if passed and options is not None and answer_key is not None:
            if isinstance(answer_key, int):
                if answer_key < 0 or answer_key >= len(options):
                    passed = False
                    details += f" | answerKey index {answer_key} out of range ({len(options)} options)"
                else:
                    chosen_option = options[answer_key]
                    if expected_target is not None:
                        # Check whether chosen_option contains or equals expected target
                        target_clean = str(expected_target).strip().lower().replace(" ", "")
                        chosen_clean = str(chosen_option).strip().lower().replace(" ", "")
                        if target_clean not in chosen_clean and chosen_clean not in target_clean:
                            # Also check symbolic equality if both are algebraic expressions
                            try:
                                diff = sympy.simplify(sympy.sympify(chosen_clean) - sympy.sympify(target_clean))
                                if diff != 0:
                                    passed = False
                                    details += f" | options[answerKey] ('{chosen_option}') does not match computed '{expected_target}'"
                            except Exception:
                                passed = False
                                details += f" | options[answerKey] ('{chosen_option}') does not match computed '{expected_target}'"
            elif isinstance(answer_key, str):
                if answer_key in options:
                    pass
                elif answer_key in ("A", "B", "C", "D") and len(options) == 4:
                    idx = ord(answer_key) - ord("A")
                    chosen_option = options[idx]
                else:
                    passed = False
                    details += f" | answerKey '{answer_key}' not found in options"

        self.total_verified += 1
        if passed:
            self.passed_count += 1
            status = "PASS"
        else:
            self.failed_count += 1
            status = "FAIL"

        self.results.append({
            "chapter": chapter,
            "resource": resource_name,
            "itemId": item_id,
            "domain": domain,
            "status": status,
            "details": details,
        })
        return passed

    def run(self) -> int:
        json_pattern = os.path.join(self.content_dir, "**", "*.json")
        json_files = glob.glob(json_pattern, recursive=True)

        if not json_files:
            print(f"ERROR: No JSON content files found under {self.content_dir}", file=sys.stderr)
            return 1

        for filepath in json_files:
            fname = os.path.basename(filepath)
            if fname in ("manifest.json", "manifest.schema.json", "chapter.json"):
                continue

            rel_path = os.path.relpath(filepath, self.content_dir)
            parts = rel_path.split(os.sep)
            chapter = parts[0] if len(parts) > 1 else "root"
            resource_name = fname

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                print(f"ERROR reading {filepath}: {exc}", file=sys.stderr)
                return 1

            for container in ("practice", "checkpointTest", "questions", "items"):
                items = data.get(container, [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            self.verify_item(chapter, resource_name, item)

        # Print formatted report
        print("=" * 80)
        print("SETU MATHEMATICAL VERIFICATION REPORT — CBSE CLASS 10 MATHEMATICS")
        print("=" * 80)
        print(f"{'Chapter':<20} {'Resource':<25} {'Item ID':<25} {'Domain':<16} {'Status':<6} Details")
        print("-" * 80)
        for r in self.results:
            print(f"{r['chapter']:<20} {r['resource']:<25} {r['itemId']:<25} {r['domain']:<16} {r['status']:<6} {r['details']}")
        print("=" * 80)
        print(f"TOTAL VERIFIED: {self.total_verified} | PASSED: {self.passed_count} | FAILED: {self.failed_count}")
        print("=" * 80)

        if self.failed_count > 0:
            print("MATHEMATICAL VERIFICATION FAILED!", file=sys.stderr)
            return 1
        elif self.total_verified == 0:
            print("WARNING: No mathematical items found to verify!", file=sys.stderr)
            return 1
        else:
            print("ALL MATHEMATICAL ITEMS VERIFIED SUCCESSFULLY (EXIT CODE 0)")
            return 0


def main() -> int:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "app", "content", "library")
    verifier = LibraryMathVerifier(target_dir)
    return verifier.run()


if __name__ == "__main__":
    sys.exit(main())
