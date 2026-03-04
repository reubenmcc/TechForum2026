"""
Utility Functions: Calculate Yield
Author: Titan Wibowo

Use Case: to back into bond book yield

"""

from scipy.optimize import newton, brentq
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np

def calculate_yield(valuation_date, maturity_date, coupon_rate,
                     value_over_par, redemption_value, frequency):
    """
    Calculate bond yield given book value over par

    Parameters:
    - valuation_date: settlement date
    - maturity_date: bond maturity date
    - coupon_rate: annual coupon rate (as decimal, e.g., 0.05 for 5%)
    - book_over_par: current book value (price)
    - redemption_value: redemption value at maturity (typically 100)
    - frequency: coupon frequency per year (1, 2, or 4)
    """

    # Convert dates if strings
    if isinstance(valuation_date, str):
        valuation_date = datetime.strptime(valuation_date, '%Y-%m-%d')
    if isinstance(maturity_date, str):
        maturity_date = datetime.strptime(maturity_date, '%Y-%m-%d')

    # Calculate time to maturity
    years_to_maturity = (maturity_date - valuation_date).days / 365.25
    num_periods = years_to_maturity * frequency

    # Coupon payment per period
    coupon_payment = (coupon_rate * 100) / frequency

    def bond_price(y):
        """
        Calculate bond price given yield per period
        Returns difference from book value (target is zero)
        """
        if abs(y) < 1e-10:  # Handle near-zero yield
            price = coupon_payment * num_periods + redemption_value
            return price - value_over_par

        # Present value of coupons
        pv_coupons = coupon_payment * (1 - (1 + y) ** (-num_periods)) / y
        # Present value of redemption
        pv_redemption = redemption_value / ((1 + y) ** num_periods)

        return pv_coupons + pv_redemption - value_over_par

    try:
        # Better initial guess: approximate yield
        initial_guess = (coupon_rate + (100 - value_over_par) / (value_over_par * years_to_maturity)) / frequency

        # Try Newton's method first
        yield_per_period = newton(bond_price, initial_guess, maxiter=100, tol=1e-8)
        annual_yield = yield_per_period * frequency
        return annual_yield

    except:
        try:
            # Fallback to Brentq method (more robust)
            # Search between -50% and +50% yield per period
            yield_per_period = brentq(bond_price, -0.5, 0.5, maxiter=100)
            annual_yield = yield_per_period * frequency
            return annual_yield
        except:
            # Return NaN if both methods fail
            return np.nan

def main():
    # Example usage
    valuation_date = '2024-12-31'
    maturity_date = '2052-05-15'
    coupon_rate = 0.01115571
    #Book Value is 515619.67
    #Par is 13378876.61
    value_over_par = 3.85398329792952
    redemption_value = 100
    frequency = 12

    yield_result = calculate_yield(valuation_date, maturity_date, coupon_rate,
                                   value_over_par, redemption_value, frequency)
    print(f"Calculated Yield: {yield_result}")


if __name__ == '__main__':
    main()