from django import template
import math

register = template.Library()

@register.filter(name='inr')
def inr_currency(value):
    """
    Format number into Indian Rupee standard (e.g., 150000 -> ₹ 1,50,000)
    """
    if value is None or value == '':
        return "₹ 0"
    try:
        val = float(value)
        is_negative = val < 0
        val = abs(val)
        
        # Split integer and decimal parts
        int_part = int(math.floor(val))
        dec_part = round(val - int_part, 2)
        dec_str = f".{int(round(dec_part * 100)):02d}" if dec_part > 0 else ""

        s = str(int_part)
        if len(s) <= 3:
            formatted = s
        else:
            last3 = s[-3:]
            remaining = s[:-3]
            groups = []
            while remaining:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            groups.reverse()
            formatted = ",".join(groups) + "," + last3

        res = f"₹ {formatted}{dec_str}"
        return f"-{res}" if is_negative else res
    except (ValueError, TypeError):
        return f"₹ {value}"

@register.filter(name='status_badge')
def status_badge_class(status):
    """
    Returns appropriate Bootstrap badge color class for Udhaar / Payment / Sale statuses.
    """
    status_map = {
        'Paid': 'bg-success-subtle text-success border-success-subtle',
        'Verified': 'bg-success-subtle text-success border-success-subtle',
        'Partially Paid': 'bg-warning-subtle text-warning border-warning-subtle',
        'Payment Promised': 'bg-info-subtle text-info border-info-subtle',
        'Due': 'bg-primary-subtle text-primary border-primary-subtle',
        'Overdue': 'bg-danger-subtle text-danger border-danger-subtle',
        'Disputed': 'bg-dark-subtle text-dark border-dark-subtle',
        'Payment Claimed': 'bg-warning-subtle text-warning border-warning-subtle',
        'Pending Verification': 'bg-info-subtle text-info border-info-subtle',
    }
    return status_map.get(status, 'bg-secondary-subtle text-secondary border-secondary-subtle')
