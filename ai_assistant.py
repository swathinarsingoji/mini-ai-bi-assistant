
import calendar
import re
from datetime import datetime


def extract_months(question):
    """
    Extract two months from a question.
    Returns month values in YYYY-MM format.
    """
    q = question.lower()

    # Find explicit YYYY-MM dates first.
    explicit_dates = re.findall(
        r"\b(20\d{2})-(0[1-9]|1[0-2])\b",
        q
    )

    if len(explicit_dates) >= 2:
        return [
            f"{year}-{month}"
            for year, month in explicit_dates[:2]
        ]

    month_names = {
        name.lower(): number
        for number, name in enumerate(calendar.month_name)
        if name
    }

    month_names.update({
        name.lower(): number
        for number, name in enumerate(calendar.month_abbr)
        if name
    })

    # Find month names in the order they appear in the question.
    pattern = (
        r"\b(january|jan|february|feb|march|mar|april|apr|"
        r"may|june|jun|july|jul|august|aug|september|sep|sept|"
        r"october|oct|november|nov|december|dec)\b"
    )

    matches = list(re.finditer(pattern, q))
    if len(matches) < 2:
        return []

    # Use a year explicitly mentioned in the question, if available.
    year_matches = re.findall(r"\b(20\d{2})\b", q)
    default_year = int(year_matches[0]) if year_matches else datetime.now().year

    results = []

    for match in matches[:2]:
        month_number = month_names[match.group(1)]

        # Prefer a year immediately following the month name.
        after_month = q[match.end():match.end() + 12]
        year_after = re.search(r"\b(20\d{2})\b", after_month)

        year = int(year_after.group(1)) if year_after else default_year
        results.append(f"{year}-{month_number:02d}")

    return results


def interpret_question(question):
    """
    Recognize supported analytics questions.

    Returns:
        (intent, params)
    """
    q = question.lower().strip()
    q = q.replace("-", " ").replace("_", " ")
    q = re.sub(r"\s+", " ", q)

    # Compare revenue between two months.
    if (
        any(word in q for word in ["compare", "change", "difference"])
        and any(word in q for word in ["revenue", "sales"])
    ):
        months = extract_months(question)

        if len(months) < 2:
            raise ValueError(
                "Please specify two months, for example: "
                "Compare revenue between January and February 2026."
            )

        return "month_comparison", {
            "month1": months[0],
            "month2": months[1],
        }

    # Total revenue.
    if any(phrase in q for phrase in [
        "total revenue",
        "overall revenue",
        "revenue overall",
        "revenue generated",
        "how much revenue",
        "total sales",
        "sum of sales",
        "sum of revenue",
    ]):
        return "total_revenue", {}

    # Monthly trend.
    if any(phrase in q for phrase in [
        "monthly",
        "month wise",
        "trend",
        "by month",
        "each month",
    ]):
        return "monthly_trend", {}

    # Top product.
    if (
        "top product" in q
        or "highest revenue" in q
        or (
            any(word in q for word in ["product", "item"])
            and any(word in q for word in [
                "highest", "top", "best", "most"
            ])
        )
    ):
        return "top_product", {}

    # Top region.
    if (
        "top region" in q
        or "highest sales" in q
        or (
            any(word in q for word in ["region", "area"])
            and any(word in q for word in [
                "highest", "top", "best", "most"
            ])
        )
    ):
        return "top_region", {}

    raise ValueError(
        "I couldn't identify that question. Try asking about total revenue, "
        "the top product, monthly trend, top region, or revenue change "
        "between two months."
    )
