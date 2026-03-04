
from scipy.optimize import brentq


def local_irr(cash_flows: list[float]) -> float:
    """
    Calculate IRR for a series of cash flows using Brent's method.

    Args:
        cash_flows: List of cash flows (first value should be negative investment)

    Returns:
        IRR as a decimal (e.g., 0.05 = 5%)
    """

    def npv(rate, flows):
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))

    try:
        irr = brentq(npv, -0.9999, 10.0, args=(cash_flows,))
        return irr
    except ValueError:
        return float('nan')

if __name__ == "__main__":
    testCashflows = [-1000000,150000,175000,200000,225000,150000,150000]
    test = local_irr(testCashflows)
    print("debug")