"""
PDF report generation for risk assessments.
Uses fpdf 1.7.2 (latin-1 only — no emojis or Unicode in generated text).
"""
from fpdf import FPDF
from datetime import datetime, timezone
from typing import Optional


def _risk_label(score: float) -> str:
    if score <= 40:  return "LOW"
    if score <= 60:  return "MODERATE"
    if score <= 80:  return "HIGH"
    return "CRITICAL"


def _risk_rgb(score: float):
    if score <= 40:  return (40, 167, 69)
    if score <= 60:  return (255, 193, 7)
    if score <= 80:  return (253, 126, 20)
    return (220, 53, 69)


def _threat_rgb(prob: float):
    if prob < 0.35:  return (40, 167, 69)
    if prob < 0.60:  return (255, 193, 7)
    return (220, 53, 69)


def _threat_label(prob: float) -> str:
    if prob < 0.35:  return "LOW"
    if prob < 0.60:  return "MODERATE"
    return "HIGH"


CATEGORY_ORDER = [
    "Physical Security",
    "Access Control",
    "Personnel",
    "Incident History",
    "Emergency Preparedness",
]

RECOMMENDATIONS = {
    "Physical Security":      "Improve perimeter integrity, upgrade lighting, and increase CCTV coverage.",
    "Access Control":         "Strengthen identity verification procedures and restrict unauthorised area access.",
    "Personnel":              "Increase guard training frequency and ensure complete shift coverage.",
    "Incident History":       "Reduce incident frequency, improve response time, and maintain documentation standards.",
    "Emergency Preparedness": "Conduct regular drills and upgrade communication and evacuation systems.",
}


def generate_pdf(assessment, ai_pred=None) -> bytes:
    """
    Generate a professional PDF report for a completed risk assessment.

    Args:
        assessment: SQLAlchemy Assessment model instance (must have category_scores,
                    overall_score, risk_level, facility_name, id, created_at).
        ai_pred:    Optional AIPrediction model instance.

    Returns:
        Raw PDF bytes.
    """
    pdf = FPDF()
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()

    page_w = pdf.w - 30   # usable width (margins excluded)
    overall = assessment.overall_score or 0.0
    category_scores = assessment.category_scores or {}
    facility = assessment.facility_name or "Unknown Facility"
    generated = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    # ── Header bar ───────────────────────────────────────────────────────────
    pdf.set_fill_color(30, 64, 175)
    pdf.rect(15, 15, page_w, 22, 'F')

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 17)
    pdf.set_xy(15, 16)
    pdf.cell(page_w, 10, "RISK SECURITY DIAGNOSTIC", ln=True, align="C")

    pdf.set_font("Arial", "", 10)
    pdf.set_xy(15, 26)
    pdf.cell(page_w, 8, "Confidential Security Assessment Report", ln=True, align="C")

    pdf.ln(6)

    # ── Metadata row ─────────────────────────────────────────────────────────
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(15, pdf.get_y(), page_w, 14, 'FD')

    pdf.set_text_color(55, 65, 81)
    pdf.set_font("Arial", "B", 9)
    pdf.set_x(17)
    pdf.cell(40, 5, "Facility:", ln=False)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, facility, ln=True)

    pdf.set_font("Arial", "B", 9)
    pdf.set_x(17)
    col_w = page_w / 3
    pdf.cell(col_w, 5, f"Assessment ID: #{assessment.id}", ln=False)
    pdf.cell(col_w, 5, f"Generated: {generated}", ln=False)
    created = assessment.created_at.strftime("%d %b %Y") if assessment.created_at else "N/A"
    pdf.cell(col_w, 5, f"Assessment Date: {created}", ln=True)

    pdf.ln(6)

    # ── Overall score box ────────────────────────────────────────────────────
    r, g, b = _risk_rgb(overall)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    box_y = pdf.get_y()
    pdf.rect(15, box_y, page_w, 28, 'F')

    pdf.set_font("Arial", "B", 28)
    pdf.set_xy(15, box_y + 2)
    pdf.cell(page_w, 12, f"{overall:.1f} / 100", ln=True, align="C")

    pdf.set_font("Arial", "B", 13)
    pdf.set_xy(15, box_y + 14)
    pdf.cell(page_w, 10, f"{_risk_label(overall)} RISK", ln=True, align="C")

    pdf.ln(8)

    # ── Category breakdown ───────────────────────────────────────────────────
    pdf.set_text_color(17, 24, 39)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Category Breakdown", ln=True)
    pdf.set_draw_color(229, 231, 235)
    pdf.line(15, pdf.get_y(), 15 + page_w, pdf.get_y())
    pdf.ln(3)

    # Table header
    pdf.set_fill_color(30, 64, 175)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    col_cat  = page_w * 0.40
    col_score = page_w * 0.15
    col_level = page_w * 0.18
    col_bar   = page_w * 0.27
    pdf.cell(col_cat,  7, "Category",    border=0, ln=False, align="L", fill=True)
    pdf.cell(col_score, 7, "Score",       border=0, ln=False, align="C", fill=True)
    pdf.cell(col_level, 7, "Risk Level",  border=0, ln=False, align="C", fill=True)
    pdf.cell(col_bar,   7, "Visual",      border=0, ln=True,  align="C", fill=True)

    pdf.set_font("Arial", "", 9)
    for i, cat in enumerate(CATEGORY_ORDER):
        score = category_scores.get(cat, 0)
        r, g, b = _risk_rgb(score)
        fill = i % 2 == 0
        pdf.set_fill_color(249, 250, 251 if fill else 255, 255)

        pdf.set_text_color(17, 24, 39)
        row_y = pdf.get_y()
        pdf.cell(col_cat,   7, cat,              border=0, ln=False, align="L",  fill=fill)
        pdf.cell(col_score, 7, f"{score:.1f}",   border=0, ln=False, align="C",  fill=fill)

        pdf.set_text_color(r, g, b)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(col_level, 7, _risk_label(score), border=0, ln=False, align="C", fill=fill)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(17, 24, 39)

        # Mini bar chart in the last column
        bar_x = pdf.get_x()
        bar_y = row_y + 1.5
        bar_max = col_bar - 4
        bar_len = (score / 100) * bar_max
        pdf.set_fill_color(229, 231, 235)
        pdf.rect(bar_x, bar_y, bar_max, 4, 'F')
        pdf.set_fill_color(r, g, b)
        if bar_len > 0:
            pdf.rect(bar_x, bar_y, bar_len, 4, 'F')
        pdf.cell(col_bar, 7, "", border=0, ln=True, fill=False)

    pdf.ln(6)

    # ── Priority recommendations ─────────────────────────────────────────────
    # Sort categories highest score first (highest risk = biggest weakness)
    sorted_cats = sorted(
        [(cat, category_scores.get(cat, 0)) for cat in CATEGORY_ORDER],
        key=lambda x: x[1], reverse=True
    )[:3]

    pdf.set_text_color(17, 24, 39)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Priority Recommendations", ln=True)
    pdf.set_draw_color(229, 231, 235)
    pdf.line(15, pdf.get_y(), 15 + page_w, pdf.get_y())
    pdf.ln(3)

    for rank, (cat, score) in enumerate(sorted_cats, 1):
        r, g, b = _risk_rgb(score)
        # Coloured left stripe
        stripe_y = pdf.get_y()
        pdf.set_fill_color(r, g, b)
        pdf.rect(15, stripe_y, 3, 14, 'F')

        pdf.set_x(20)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(17, 24, 39)
        pdf.cell(0, 6, f"{rank}. {cat}  (Score: {score:.1f})", ln=True)
        pdf.set_x(20)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(75, 85, 99)
        pdf.multi_cell(page_w - 5, 5, RECOMMENDATIONS.get(cat, "Review this category."))
        pdf.ln(2)

    # ── AI Predictions (if available) ────────────────────────────────────────
    if ai_pred:
        # New page if less than 60mm remaining
        if pdf.get_y() > pdf.h - 75:
            pdf.add_page()

        pdf.set_text_color(17, 24, 39)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "AI Risk Predictions (RandomForest)", ln=True)
        pdf.set_draw_color(229, 231, 235)
        pdf.line(15, pdf.get_y(), 15 + page_w, pdf.get_y())
        pdf.ln(3)

        threats = [
            ("Unauthorized Access", ai_pred.unauthorized_access_prob),
            ("Insider Threat",       ai_pred.insider_threat_prob),
            ("Emergency Failure",    ai_pred.emergency_failure_prob),
            ("Perimeter Breach",     ai_pred.perimeter_breach_prob),
        ]
        col_name  = page_w * 0.42
        col_pct   = page_w * 0.18
        col_level2 = page_w * 0.18
        col_bar2  = page_w * 0.22

        # Table header
        pdf.set_fill_color(30, 64, 175)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(col_name,  7, "Threat Vector",    border=0, ln=False, align="L", fill=True)
        pdf.cell(col_pct,   7, "Probability",       border=0, ln=False, align="C", fill=True)
        pdf.cell(col_level2, 7, "Level",            border=0, ln=False, align="C", fill=True)
        pdf.cell(col_bar2,  7, "Visual",            border=0, ln=True,  align="C", fill=True)

        pdf.set_font("Arial", "", 9)
        for i, (name, prob) in enumerate(threats):
            if prob is None:
                continue
            r, g, b = _threat_rgb(prob)
            fill = i % 2 == 0
            pdf.set_fill_color(249, 250, 251 if fill else 255, 255)
            pdf.set_text_color(17, 24, 39)

            row_y = pdf.get_y()
            pdf.cell(col_name,  7, name,                   border=0, ln=False, align="L",  fill=fill)
            pdf.cell(col_pct,   7, f"{prob * 100:.1f}%",   border=0, ln=False, align="C",  fill=fill)

            pdf.set_text_color(r, g, b)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(col_level2, 7, _threat_label(prob),   border=0, ln=False, align="C",  fill=fill)
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(17, 24, 39)

            bar_x  = pdf.get_x()
            bar_y  = row_y + 1.5
            bar_max = col_bar2 - 4
            bar_len = prob * bar_max
            pdf.set_fill_color(229, 231, 235)
            pdf.rect(bar_x, bar_y, bar_max, 4, 'F')
            pdf.set_fill_color(r, g, b)
            if bar_len > 0:
                pdf.rect(bar_x, bar_y, bar_len, 4, 'F')
            pdf.cell(col_bar2, 7, "", border=0, ln=True, fill=False)

    # ── Footer ───────────────────────────────────────────────────────────────
    pdf.set_y(-18)
    pdf.set_draw_color(203, 213, 225)
    pdf.line(15, pdf.get_y(), 15 + page_w, pdf.get_y())
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(156, 163, 175)
    pdf.set_x(15)
    pdf.cell(page_w / 2, 8, "Generated by Risk Security Diagnostic Platform", ln=False, align="L")
    pdf.cell(page_w / 2, 8, f"Page {pdf.page_no()}", ln=False, align="R")

    raw = pdf.output(dest="S")
    return raw if isinstance(raw, bytes) else raw.encode("latin-1")
