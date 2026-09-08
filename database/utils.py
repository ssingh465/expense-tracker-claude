from datetime import datetime, date, timedelta

def validate_date_range(date_from, date_to):
    """
    Validates that dates are in YYYY-MM-DD format and that start date is before end date.

    Returns:
        (validated_from, validated_to, error_message)
    """
    validated_from = None
    validated_to = None

    try:
        if date_from:
            datetime.strptime(date_from, "%Y-%m-%d")
            validated_from = date_from
        if date_to:
            datetime.strptime(date_to, "%Y-%m-%d")
            validated_to = date_to
    except ValueError:
        return None, None, "Invalid date format. Please use YYYY-MM-DD."

    if validated_from and validated_to and validated_from > validated_to:
        return None, None, "Start date must be before end date."

    return validated_from, validated_to, None

def get_date_presets():
    """
    Calculates ISO date strings for common period presets.

    Returns:
        A dictionary mapping preset keys to (start_date, end_date) tuples.
    """
    today = date.today()

    # This Month: 1st of current month to today
    this_month_start = today.replace(day=1).isoformat()
    this_month_end = today.isoformat()

    # Last 3 Months: 90 days ago to today
    last_3m_start = (today - timedelta(days=90)).isoformat()
    last_3m_end = today.isoformat()

    # Last 6 Months: 180 days ago to today
    last_6m_start = (today - timedelta(days=180)).isoformat()
    last_6m_end = today.isoformat()

    return {
        "this_month": (this_month_start, this_month_end),
        "last_3m": (last_3m_start, last_3m_end),
        "last_6m": (last_6m_start, last_6m_end),
    }
