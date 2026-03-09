import os
import random
import sqlite3
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Setting DB path to default
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB_PATH = os.path.join(_PROJECT_ROOT, "agentDocs", "DB", "alfa_cashflows.db")
# ---------------------------------------------------------------------------
# Line-of-business registry
# Maps LOB codes to human-readable names.
# ---------------------------------------------------------------------------
LOB_REGISTRY = {
    "TLIFE": {"name": "Term Life"},
    "WLIFE": {"name": "Whole Life"},
    "FANN":  {"name": "Fixed Annuity"},
    "LTC":   {"name": "Long-Term Care"},
    "GRP":   {"name": "Group Benefits"},
}

# ---------------------------------------------------------------------------
# Sensitivity scenario definitions
#
#   mortality_shock  : additive shift on benefit draw rate  (e.g. +0.10 = +10%)
#   interest_shock   : additive shift on discount/reserve rate (e.g. +0.01 = +100bps)
#   expense_shock    : additive shift on expense draw rate  (e.g. +0.10 = +10%)
# ---------------------------------------------------------------------------
@dataclass
class Scenario:
    label: str
    mortality_shock: float = 0.0
    interest_shock:  float = 0.0
    expense_shock:   float = 0.0


SCENARIOS: dict[str, Scenario] = {
    "BASE":     Scenario(label="Base"),
    "MORT_UP":  Scenario(label="Mortality +10%",        mortality_shock=+0.10),
    "INT_UP":   Scenario(label="Interest Rate +100bps", interest_shock=+0.01),
    "INT_DOWN": Scenario(label="Interest Rate -100bps", interest_shock=-0.01),
    "EXP_UP":   Scenario(label="Expense +10%",          expense_shock=+0.10),
}

# ---------------------------------------------------------------------------
# SQLite DDL
# A single table holds both base and sensitivity runs, distinguished by the
# 'scenario' and 'scenario_label' columns.
# ---------------------------------------------------------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS alfa_cashflows (
    id               INTEGER  PRIMARY KEY AUTOINCREMENT,
    lob_code         TEXT     NOT NULL,
    lob_name         TEXT     NOT NULL,
    year             INTEGER  NOT NULL,
    quarter          INTEGER  NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    scenario         TEXT     NOT NULL DEFAULT 'BASE',
    scenario_label   TEXT     NOT NULL DEFAULT 'Base',
    mortality_shock  REAL     NOT NULL DEFAULT 0.0,
    interest_shock   REAL     NOT NULL DEFAULT 0.0,
    expense_shock    REAL     NOT NULL DEFAULT 0.0,
    period           INTEGER  NOT NULL,
    premium_cf       REAL     NOT NULL,
    benefit_cf       REAL     NOT NULL,
    expense_cf       REAL     NOT NULL,
    net_cf           REAL     NOT NULL,
    reserve          REAL     NOT NULL,
    discount_rate    REAL     NOT NULL,
    run_elapsed_s    REAL     NOT NULL,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _get_connection(db_path: str) -> sqlite3.Connection:
    """Open (or create) the SQLite database and ensure the table exists."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    return conn


def _project_cashflows(
    lob_code: str,
    lob_name: str,
    year: int,
    quarter: int,
    scenario: Scenario,
    elapsed: float,
    ) -> list[tuple]:
    """
    Generate 20-period cash-flow projections for a single scenario.
    Shocks from the Scenario object are applied to the base draw rates.
    """
    BASE_DISCOUNT_RATE = 0.05
    discount_rate = BASE_DISCOUNT_RATE + scenario.interest_shock

    rows = []
    reserve = random.uniform(50_000_000, 200_000_000)

    for t in range(1, 21):
        prem = round(reserve * random.uniform(0.04, 0.06), 2)

        # Mortality shock shifts the benefit draw range up (more deaths = higher claims)
        benefit = -round(
            reserve * random.uniform(
                0.03 + scenario.mortality_shock,
                0.05 + scenario.mortality_shock,
            ), 2
        )

        # Expense shock shifts the expense draw range up
        expense = -round(
            reserve * random.uniform(
                0.005 + scenario.expense_shock,
                0.015 + scenario.expense_shock,
            ), 2
        )

        net = round(prem + benefit + expense, 2)

        # Interest shock feeds into reserve roll-forward
        reserve = round(
            reserve * random.uniform(
                0.97 + scenario.interest_shock,
                1.02 + scenario.interest_shock,
            ), 2
        )

        rows.append((
            lob_code,
            lob_name,
            year,
            quarter,
            scenario.label,          # scenario key used as identifier
            scenario.label,          # scenario_label (human-readable)
            scenario.mortality_shock,
            scenario.interest_shock,
            scenario.expense_shock,
            t,
            prem,
            benefit,
            expense,
            net,
            reserve,
            discount_rate,
            elapsed,
        ))

    return rows


def run_alfa(
    lob_code: str,
    quarter: int,
    year: int,
    db_path: str = _DEFAULT_DB_PATH,
    scenarios: Optional[list[str]] = None,
    ) -> str:
    """
    Run the Mg-Alfa cash-flow model for a given LOB, quarter, and year.
    Optionally runs sensitivity scenarios alongside the base run. All results
    land in a single SQLite table with a 'scenario' column to distinguish them.

    Parameters
    ----------
    lob_code  : str        - LOB identifier (e.g. 'TLIFE')
    quarter   : int        - Reporting quarter (1-4)
    year      : int        - Reporting year (e.g. 2024)
    db_path   : str        - Path to the SQLite database file
    scenarios : list[str]  - Scenario keys to run in addition to 'BASE'.
                             Valid keys: MORT_UP, INT_UP, INT_DOWN, EXP_UP
                             Pass None or [] to run BASE only.
                             Pass ['ALL'] to run every available scenario.

    Returns
    -------
    str - Summary message describing the outcome of all runs.

    Examples
    --------
    # Base only
    run_alfa("TLIFE", quarter=1, year=2024)

    # Base + two sensitivities
    run_alfa("TLIFE", quarter=1, year=2024, scenarios=["MORT_UP", "INT_UP"])

    # Base + all sensitivities
    run_alfa("TLIFE", quarter=1, year=2024, scenarios=["ALL"])
    """
    # --- Validate inputs -----------------------------------------------------
    lob = LOB_REGISTRY.get(lob_code.upper())
    if lob is None:
        return f"Unknown LOB code '{lob_code}'."

    if quarter not in (1, 2, 3, 4):
        return f"Invalid quarter '{quarter}'. Must be 1, 2, 3, or 4."

    # Resolve which scenarios to run
    if not scenarios:
        keys_to_run = ["BASE"]
    elif "ALL" in [s.upper() for s in scenarios]:
        keys_to_run = list(SCENARIOS.keys())
    else:
        normalised = [s.upper() for s in scenarios]
        invalid = [s for s in normalised if s not in SCENARIOS]
        if invalid:
            return (
                f"Unknown scenario key(s): {invalid}. "
                f"Valid keys: {list(SCENARIOS.keys())}"
            )
        # Always include BASE; avoid duplicates
        keys_to_run = ["BASE"] + [s for s in normalised if s != "BASE"]

    # --- Project cash flows for each scenario --------------------------------
    all_rows: list[tuple] = []
    elapsed = round(random.uniform(2.5, 8.0), 1)

    for key in keys_to_run:
        rows = _project_cashflows(
            lob_code=lob_code.upper(),
            lob_name=lob["name"],
            year=year,
            quarter=quarter,
            scenario=SCENARIOS[key],
            elapsed=elapsed,
        )
        all_rows.extend(rows)

    # --- Persist to SQLite ---------------------------------------------------
    insert_sql = """
        INSERT INTO alfa_cashflows (
            lob_code, lob_name, year, quarter,
            scenario, scenario_label,
            mortality_shock, interest_shock, expense_shock,
            period, premium_cf, benefit_cf, expense_cf,
            net_cf, reserve, discount_rate, run_elapsed_s
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn = _get_connection(db_path)
    try:
        conn.executemany(insert_sql, all_rows)
        conn.commit()
    finally:
        conn.close()
    # -------------------------------------------------------------------------

    scenario_summary = ", ".join(SCENARIOS[k].label for k in keys_to_run)
    return (
        f"Mg-Alfa run complete for {lob['name']} ({lob_code.upper()}) "
        f"Q{quarter} {year}. "
        f"Scenarios: [{scenario_summary}]. "
        f"{len(all_rows)} total rows written to '{db_path}'. "
        f"Elapsed: {elapsed}s."
    )


def run_alfa_all_sensitivities(
    lob_code: str,
    quarter: int,
    year: int,
    db_path: str = _DEFAULT_DB_PATH,
) -> str:
    """Convenience wrapper — runs BASE + all four sensitivity scenarios."""
    return run_alfa(lob_code, quarter, year, db_path, scenarios=["ALL"])

if __name__ == "__main__":
    run_alfa("TLIFE", quarter=1, year=2024, scenarios=["MORT_UP", "INT_UP"])