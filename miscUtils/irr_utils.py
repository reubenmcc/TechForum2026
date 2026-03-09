"""
irr_utils.py
------------
Newton-Raphson IRR solver that reads directly from the alfa_cashflows SQLite
database and returns results by scenario and quarter.

SQLite has no native IRR function — this module bridges the gap by pulling
cash flows from the v_irr_inputs view and solving iteratively in Python.

Functions
---------
compute_irr(cash_flows)                  – core solver (pure Python, no deps)
compute_irr_from_db(...)                 – query DB + solve for one slice
irr_by_scenario(...)                     – IRR for every scenario in a quarter
irr_by_quarter(...)                      – IRR for every quarter for one scenario
irr_full_matrix(...)                     – IRR for all LOBs × scenarios × quarters
"""

import sqlite3
from typing import Optional


# ---------------------------------------------------------------------------
# Core IRR solver  —  Newton-Raphson
# ---------------------------------------------------------------------------

def compute_irr(
    cash_flows: list[float],
    guess: float = 0.10,
    tol: float = 1e-7,
    max_iter: int = 1_000,
) -> Optional[float]:
    """
    Estimate the Internal Rate of Return for a series of cash flows using
    Newton-Raphson iteration.

    Parameters
    ----------
    cash_flows : list[float]
        Ordered cash flows.  The first element is treated as period 1
        (no period-0 investment in this model; all flows are operating CFs).
    guess      : float   Starting rate (default 10 %)
    tol        : float   Convergence tolerance
    max_iter   : int     Maximum iterations before giving up

    Returns
    -------
    float | None – IRR as a decimal (e.g. 0.087 = 8.7 %), or None if the
                   solver did not converge.
    """
    r = guess

    for _ in range(max_iter):
        try:
            npv  = sum(cf / (1.0 + r) ** (t + 1) for t, cf in enumerate(cash_flows))
            dnpv = sum(-(t + 1) * cf / (1.0 + r) ** (t + 2) for t, cf in enumerate(cash_flows))
        except (OverflowError, ZeroDivisionError):
            return None

        if dnpv == 0:
            return None   # flat derivative — can't converge

        r_new = r - npv / dnpv

        # Clamp to prevent divergence into extreme territory
        r_new = max(-0.999, min(r_new, 100.0))

        if abs(r_new - r) < tol:
            return round(r_new, 6)

        r = r_new

    # Retry with a different starting guess if first attempt failed
    if guess != 0.01:
        return compute_irr(cash_flows, guess=0.01, tol=tol, max_iter=max_iter)

    return None   # did not converge within max_iter


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_cash_flows(
    conn: sqlite3.Connection,
    lob_code: str,
    year: int,
    quarter: int,
    scenario: str,
) -> list[float]:
    """Pull ordered net_cf values for one LOB / year / quarter / scenario."""
    rows = conn.execute(
        """
        SELECT net_cf
        FROM   v_irr_inputs
        WHERE  lob_code = ?
          AND  year     = ?
          AND  quarter  = ?
          AND  scenario = ?
        ORDER  BY period
        """,
        (lob_code.upper(), year, quarter, scenario),
    ).fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_irr_from_db(
    lob_code: str,
    year: int,
    quarter: int,
    scenario: str = "Base",
    db_path: str = "agentDocs/cashflows/alfa_cashflows.db",
) -> dict:
    """
    Compute IRR for a single LOB / year / quarter / scenario slice.

    Returns
    -------
    dict with keys: lob_code, year, quarter, scenario, irr, irr_pct, periods
    """
    conn = sqlite3.connect(db_path)
    try:
        cfs = _fetch_cash_flows(conn, lob_code, year, quarter, scenario)
    finally:
        conn.close()

    if not cfs:
        return {"error": f"No cash flows found for {lob_code} Q{quarter} {year} [{scenario}]"}

    irr = compute_irr(cfs)
    return {
        "lob_code": lob_code.upper(),
        "year":     year,
        "quarter":  quarter,
        "scenario": scenario,
        "irr":      irr,
        "irr_pct":  f"{irr * 100:.4f}%" if irr is not None else "No convergence",
        "periods":  len(cfs),
    }


def irr_by_scenario(
    lob_code: str,
    year: int,
    quarter: int,
    db_path: str = "agentDocs/cashflows/alfa_cashflows.db",
) -> list[dict]:
    """
    Compute IRR for every scenario present in the DB for a given
    LOB / year / quarter.  Useful for comparing base vs. stress results.

    Returns
    -------
    list[dict] – one dict per scenario, sorted by scenario label.

    Example
    -------
    results = irr_by_scenario("TLIFE", year=2024, quarter=1)
    for r in results:
        print(r["scenario"], r["irr_pct"])
    """
    conn = sqlite3.connect(db_path)
    try:
        scenarios = conn.execute(
            """
            SELECT DISTINCT scenario, scenario_label
            FROM   v_irr_inputs
            WHERE  lob_code = ?
              AND  year     = ?
              AND  quarter  = ?
            ORDER  BY scenario_label
            """,
            (lob_code.upper(), year, quarter),
        ).fetchall()

        results = []
        for (scenario, scenario_label) in scenarios:
            cfs = _fetch_cash_flows(conn, lob_code, year, quarter, scenario)
            irr = compute_irr(cfs)
            results.append({
                "lob_code":       lob_code.upper(),
                "year":           year,
                "quarter":        quarter,
                "scenario":       scenario,
                "scenario_label": scenario_label,
                "irr":            irr,
                "irr_pct":        f"{irr * 100:.4f}%" if irr is not None else "No convergence",
                "periods":        len(cfs),
            })
    finally:
        conn.close()

    return results


def irr_by_quarter(
    lob_code: str,
    year: int,
    scenario: str = "Base",
    db_path: str = "agentDocs/cashflows/alfa_cashflows.db",
) -> list[dict]:
    """
    Compute IRR for every quarter present in the DB for a given
    LOB / year / scenario.  Useful for tracking quarter-over-quarter movement.

    Returns
    -------
    list[dict] – one dict per quarter, sorted by quarter.

    Example
    -------
    results = irr_by_quarter("TLIFE", year=2024, scenario="Base")
    for r in results:
        print(f"Q{r['quarter']}: {r['irr_pct']}")
    """
    conn = sqlite3.connect(db_path)
    try:
        quarters = conn.execute(
            """
            SELECT DISTINCT quarter
            FROM   v_irr_inputs
            WHERE  lob_code = ?
              AND  year     = ?
              AND  scenario = ?
            ORDER  BY quarter
            """,
            (lob_code.upper(), year, scenario),
        ).fetchall()

        results = []
        for (quarter,) in quarters:
            cfs = _fetch_cash_flows(conn, lob_code, year, quarter, scenario)
            irr = compute_irr(cfs)
            results.append({
                "lob_code": lob_code.upper(),
                "year":     year,
                "quarter":  quarter,
                "scenario": scenario,
                "irr":      irr,
                "irr_pct":  f"{irr * 100:.4f}%" if irr is not None else "No convergence",
                "periods":  len(cfs),
            })
    finally:
        conn.close()

    return results


def irr_full_matrix(
    year: int,
    quarter: int,
    db_path: str = "agentDocs/DB/alfa_cashflows.db",
) -> list[dict]:
    """
    Compute IRR for every LOB × scenario combination for a given year and
    quarter.  Returns a flat list that can be easily loaded into a DataFrame.

    Returns
    -------
    list[dict] – one dict per LOB × scenario, sorted by LOB then scenario.

    Example
    -------
    matrix = irr_full_matrix(year=2024, quarter=1)
    for r in matrix:
        print(r["lob_code"], r["scenario_label"], r["irr_pct"])
    """
    conn = sqlite3.connect(db_path)
    try:
        combos = conn.execute(
            """
            SELECT DISTINCT lob_code, scenario, scenario_label
            FROM   v_irr_inputs
            WHERE  year    = ?
              AND  quarter = ?
            ORDER  BY lob_code, scenario_label
            """,
            (year, quarter),
        ).fetchall()

        results = []
        for (lob_code, scenario, scenario_label) in combos:
            cfs = _fetch_cash_flows(conn, lob_code, year, quarter, scenario)
            irr = compute_irr(cfs)
            results.append({
                "lob_code":       lob_code,
                "year":           year,
                "quarter":        quarter,
                "scenario":       scenario,
                "scenario_label": scenario_label,
                "irr":            irr,
                "irr_pct":        f"{irr * 100:.4f}%" if irr is not None else "No convergence",
                "periods":        len(cfs),
            })
    finally:
        conn.close()

    return results