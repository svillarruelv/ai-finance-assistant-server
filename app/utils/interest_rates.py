"""Interest rate conversion utilities.

Provides functions to convert between different interest rate types:
- TEA (Tasa Efectiva Anual) - Annual Effective Rate
- TEM (Tasa Efectiva Mensual) - Monthly Effective Rate  
- TED (Tasa Efectiva Diaria) - Daily Effective Rate
"""

from decimal import Decimal, ROUND_HALF_UP


def tea_to_tem(annual_rate_pct: Decimal) -> Decimal:
    """Convert annual effective rate (TEA) to monthly effective rate (TEM).
    
    Formula: TEM = (1 + TEA)^(1/12) - 1
    
    Args:
        annual_rate_pct: Annual rate as percentage (e.g., 45.0 for 45%)
    
    Returns:
        Monthly effective rate as percentage (e.g., 3.14 for 3.14%)
    """
    tea_decimal = annual_rate_pct / Decimal("100")
    tem_decimal = (Decimal("1") + tea_decimal) ** (Decimal("1") / Decimal("12")) - Decimal("1")
    return (tem_decimal * Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def tea_to_ted(annual_rate_pct: Decimal) -> Decimal:
    """Convert annual effective rate (TEA) to daily effective rate (TED).
    
    Formula: TED = (1 + TEA)^(1/365) - 1
    
    Args:
        annual_rate_pct: Annual rate as percentage (e.g., 45.0 for 45%)
    
    Returns:
        Daily effective rate as percentage (e.g., 0.1027 for 0.1027%)
    """
    tea_decimal = annual_rate_pct / Decimal("100")
    ted_decimal = (Decimal("1") + tea_decimal) ** (Decimal("1") / Decimal("365")) - Decimal("1")
    return (ted_decimal * Decimal("100")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
