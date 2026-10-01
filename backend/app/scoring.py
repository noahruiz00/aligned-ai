"""Wealth Alignment Score engine.

Deterministic and explainable by design: every point can be traced to an input,
so an advisor can walk a client through exactly why a category scored as it did.
The client's own values (from the discovery conversation) change which gaps matter
most and how the categories are weighted in the overall score.
"""

from .schemas import FinancialPortrait

THEMES = {
    "impact": ["environment", "climate", "sustainab", "impact", "planet", "esg", "conservation", "social justice", "equity"],
    "family": ["family", "children", "kids", "parents", "generation", "heirs", "grandchild", "security", "home"],
    "generosity": ["giving", "philanthrop", "charit", "service", "community", "donat", "foundation", "contribut", "education"],
    "freedom": ["freedom", "autonomy", "independence", "travel", "time", "flexibility"],
}

CATEGORY_META = {
    "cash_flow": ("Cash Flow", "Are spending habits aligned with personal values?"),
    "investment": ("Investment", "Does the portfolio reflect your purpose?"),
    "estate": ("Estate & Legacy", "Does your plan transfer values, not only assets?"),
    "philanthropy": ("Philanthropy", "Is your giving aligned with the causes you care about?"),
    "risk": ("Risk Management", "Is the vision protected against what could derail it?"),
}


def _flatten(values: dict | None) -> str:
    if not values:
        return ""
    parts: list[str] = []
    for v in values.get("values", []):
        parts.append(f"{v.get('name', '')} {v.get('why', '')}")
    for key in ("financial_priorities", "life_goals", "family_goals", "legacy_goals", "philanthropy"):
        parts.extend(values.get(key, []))
    return " ".join(parts).lower()


def detect_themes(values: dict | None) -> set[str]:
    text = _flatten(values)
    return {theme for theme, words in THEMES.items() if any(w in text for w in words)}


def _clamp(x: float) -> int:
    return max(5, min(100, round(x)))


def _top_values(values: dict | None, n: int = 2) -> str:
    names = [v.get("name", "") for v in (values or {}).get("values", [])][:n]
    return " and ".join(n.lower() for n in names if n) or "your stated priorities"


def calculate(portrait: FinancialPortrait, values: dict | None) -> dict:
    p = portrait
    themes = detect_themes(values)
    top = _top_values(values)
    cats: dict[str, dict] = {}

    # --- Cash flow -------------------------------------------------------
    score = p.spending_on_priorities_pct * 0.8 + (20 if p.has_spending_plan else 5)
    recs = []
    if p.spending_on_priorities_pct < 60:
        recs.append(f"Review last quarter's spending against {top} to see what could be redirected toward what matters most.")
    if not p.has_spending_plan:
        recs.append("Co-create a values-first spending plan that funds priorities before discretionary spending.")
    if not recs:
        recs.append("Revisit the spending plan annually as life priorities evolve.")
    cats["cash_flow"] = {
        "score": _clamp(score),
        "explanation": f"About {p.spending_on_priorities_pct}% of discretionary spending flows toward {top}"
        + (", supported by a written spending plan." if p.has_spending_plan else ", without a written plan to anchor it."),
        "recommendations": recs,
    }

    # --- Investment ------------------------------------------------------
    target = 40 if "impact" in themes else 25
    review_pts = {"yes": 40, "partly": 25, "no": 8}[p.portfolio_values_review]
    score = min(p.values_aligned_allocation_pct / target, 1) * 60 + review_pts
    recs = []
    if p.portfolio_values_review != "yes":
        recs.append("Walk through the current portfolio with your advisor using the Wealth Purpose Statement as the lens.")
    if p.values_aligned_allocation_pct < target:
        recs.append(
            "Discuss with your advisor whether values-aligned or impact strategies could fit your risk profile and goals."
            if "impact" in themes
            else "Explore with your advisor how holdings could better reflect the values you named."
        )
    if not recs:
        recs.append("Add impact reporting to your annual review to track alignment over time.")
    cats["investment"] = {
        "score": _clamp(score),
        "explanation": f"{p.values_aligned_allocation_pct}% of the portfolio is intentionally values-aligned"
        + (" — below what your emphasis on impact suggests." if "impact" in themes and p.values_aligned_allocation_pct < target else ".")
        + {"yes": " It has been reviewed against your values.", "partly": " It has been partially reviewed against your values.", "no": " It has not yet been reviewed against your values."}[p.portfolio_values_review],
        "recommendations": recs,
    }

    # --- Estate & legacy -------------------------------------------------
    conv_pts = {"regular": 30, "occasional": 18, "never": 5}[p.family_conversations]
    score = (25 if p.has_will else 0) + (20 if p.has_trust else 0) + (25 if p.has_legacy_letter else 0) + conv_pts
    missing = [label for ok, label in ((p.has_will, "a will"), (p.has_trust, "a trust"), (p.has_legacy_letter, "a legacy letter")) if not ok]
    recs = []
    if not p.has_legacy_letter:
        recs.append("Draft a legacy letter (ethical will) so heirs inherit the story and values behind the wealth.")
    if p.family_conversations != "regular":
        recs.append("Plan a facilitated family conversation about the purpose of the family's wealth.")
    if not p.has_will or not p.has_trust:
        recs.append("Review estate documents with counsel so the structure reflects your Wealth Purpose Statement.")
    cats["estate"] = {
        "score": _clamp(score),
        "explanation": ("Core documents are in place" if not missing else f"No {' or '.join(m[2:] for m in missing)} yet")
        + "; family conversations about wealth "
        + {"regular": "happen regularly.", "occasional": "happen occasionally.", "never": "rarely happen."}[p.family_conversations],
        "recommendations": recs or ["Revisit documents after major life events to keep them aligned with purpose."],
    }

    # --- Philanthropy ----------------------------------------------------
    target = 5.0 if "generosity" in themes else 3.0
    align_pts = {"intentional": 40, "somewhat": 25, "ad_hoc": 10}[p.giving_alignment]
    score = min(p.annual_giving_pct / target, 1) * 40 + align_pts + (20 if p.has_giving_vehicle else 5)
    recs = []
    if p.giving_alignment != "intentional":
        recs.append("Define two or three focus causes drawn from your values, and a simple giving policy for them.")
    if not p.has_giving_vehicle and p.annual_giving_pct >= 2:
        recs.append("Ask your advisor whether a giving vehicle such as a donor-advised fund suits your plans.")
    if "generosity" in themes and p.annual_giving_pct < target:
        recs.append("Giving is central to your purpose — consider setting an intentional annual giving goal.")
    cats["philanthropy"] = {
        "score": _clamp(score),
        "explanation": f"Giving is about {p.annual_giving_pct:g}% of income and is "
        + {"intentional": "intentionally directed to chosen causes", "somewhat": "partly directed to chosen causes", "ad_hoc": "mostly ad hoc"}[p.giving_alignment]
        + ".",
        "recommendations": recs or ["Add an annual impact review so giving decisions build on what's working."],
    }

    # --- Risk ------------------------------------------------------------
    score = min(p.emergency_reserve_months / 6, 1) * 40 + (30 if p.insurance_reviewed_recently else 10) + (0 if p.concentrated_position else 30)
    recs = []
    if p.emergency_reserve_months < 6:
        recs.append("Discuss an appropriate cash reserve so short-term surprises never force long-term compromises.")
    if not p.insurance_reviewed_recently:
        recs.append("Schedule an insurance review covering life, disability, and property & casualty.")
    if p.concentrated_position:
        recs.append("Talk through the concentrated position with your advisor and how it relates to your goals.")
    cats["risk"] = {
        "score": _clamp(score),
        "explanation": f"{p.emergency_reserve_months} months of reserves; insurance "
        + ("reviewed recently" if p.insurance_reviewed_recently else "not reviewed recently")
        + ("; one concentrated position." if p.concentrated_position else "; no single concentrated position."),
        "recommendations": recs or ["Keep protections current as the family and assets grow."],
    }

    # --- Weighting by values ---------------------------------------------
    weights = {k: 1.0 for k in cats}
    rationale = []
    if "impact" in themes:
        weights["investment"] += 0.3
        weights["philanthropy"] += 0.2
        rationale.append("Investment and philanthropy weigh more because you emphasised impact.")
    if "family" in themes:
        weights["estate"] += 0.3
        weights["risk"] += 0.1
        rationale.append("Estate & legacy weighs more because family is central to your purpose.")
    if "generosity" in themes:
        weights["philanthropy"] += 0.3
        rationale.append("Philanthropy weighs more because contribution is part of your purpose.")
    if "freedom" in themes:
        weights["cash_flow"] += 0.2
        rationale.append("Cash flow weighs more because freedom and flexibility matter to you.")

    for key, (label, question) in CATEGORY_META.items():
        cats[key].update(label=label, question=question, weight=round(weights[key], 2))

    overall = round(sum(cats[k]["score"] * weights[k] for k in cats) / sum(weights.values()))
    return {
        "overall": overall,
        "categories": cats,
        "themes": sorted(themes),
        "weighting_rationale": rationale or ["All five areas are weighted equally."],
    }
