"""PDF generation for system assessment reports."""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, ListFlowable, ListItem
)

from app.models.system import System
from app.models.assessment import RiskAssessment
from app.schemas.assessment import DATA_TYPES


def get_tier_color(tier: str) -> colors.Color:
    """Get color for risk tier."""
    tier_colors = {
        "Low": colors.Color(0.2, 0.7, 0.3),      # Green
        "Moderate": colors.Color(0.9, 0.7, 0.1),  # Yellow
        "High": colors.Color(0.9, 0.4, 0.1),      # Orange
        "Critical": colors.Color(0.8, 0.2, 0.2),  # Red
    }
    return tier_colors.get(tier, colors.gray)


def generate_system_pdf(system: System, assessment: RiskAssessment) -> bytes:
    """
    Generate a PDF report for a system assessment.

    Returns PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=6,
    )
    normal_style = styles['Normal']
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
    )

    story = []

    # Title
    story.append(Paragraph(f"Student Data Risk Assessment", title_style))
    story.append(Paragraph(f"<b>{system.name}</b>", styles['Heading2']))
    story.append(Spacer(1, 12))

    # Metadata
    meta_data = [
        ["Generated:", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
        ["Assessment Date:", assessment.assessed_at.strftime("%Y-%m-%d")],
        ["Purpose:", system.purpose_category.value],
    ]
    if system.vendor:
        meta_data.append(["Vendor:", system.vendor])
    if system.owner_department:
        meta_data.append(["Owner Department:", system.owner_department])

    meta_table = Table(meta_data, colWidths=[1.5*inch, 4*inch])
    meta_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 20))

    # Risk Score Box
    tier_color = get_tier_color(assessment.risk_tier.value)
    score_data = [
        [f"Risk Score: {assessment.score_total}/100", f"Risk Tier: {assessment.risk_tier.value}"]
    ]
    score_table = Table(score_data, colWidths=[3*inch, 3*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('TEXTCOLOR', (1, 0), (1, 0), tier_color),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BOX', (0, 0), (-1, -1), 1, tier_color),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 20))

    # Score Breakdown
    story.append(Paragraph("Score Breakdown", heading_style))
    breakdown = assessment.score_breakdown_json
    breakdown_data = [
        ["Category", "Score", "Max"],
        ["Data Sensitivity", str(breakdown.get("sensitivity", 0)), "30"],
        ["Exposure Risk", str(breakdown.get("exposure", 0)), "25"],
        ["Security Controls", str(breakdown.get("security_controls", 0)), "20"],
        ["Vendor Posture", str(breakdown.get("vendor_posture", 0)), "15"],
        ["Integration Risk", str(breakdown.get("integration_blast_radius", 0)), "10"],
    ]
    breakdown_table = Table(breakdown_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(breakdown_table)
    story.append(Spacer(1, 20))

    # Key Risk Factors
    story.append(Paragraph("Key Risk Factors", heading_style))
    reason_codes = assessment.reason_codes_json[:5] if assessment.reason_codes_json else []

    if reason_codes:
        risk_items = []
        for rc in reason_codes:
            risk_items.append(
                ListItem(
                    Paragraph(f"<b>{rc['code']}</b>: {rc['explanation']}", normal_style),
                    leftIndent=10,
                )
            )
        story.append(ListFlowable(risk_items, bulletType='bullet'))
    else:
        story.append(Paragraph("No significant risk factors identified.", normal_style))

    story.append(Spacer(1, 20))

    # Data Types Collected
    story.append(Paragraph("Data Types Collected", heading_style))
    answers = assessment.answers_json
    data_types = answers.get("data_types", [])

    if answers.get("data_types_unknown"):
        story.append(Paragraph("<i>Data types are unknown or not specified.</i>", normal_style))
    elif data_types:
        dt_items = []
        for dt in data_types:
            label = DATA_TYPES.get(dt, dt)
            dt_items.append(ListItem(Paragraph(label, normal_style), leftIndent=10))
        story.append(ListFlowable(dt_items, bulletType='bullet'))
    else:
        story.append(Paragraph("No data types specified.", normal_style))

    story.append(Spacer(1, 20))

    # Storage and Security
    story.append(Paragraph("Storage & Security Summary", heading_style))
    summary_data = [
        ["Storage Location:", _format_answer(answers.get("storage_location"))],
        ["Data Region:", _format_answer(answers.get("data_region"))],
        ["SSO Supported:", _format_answer(answers.get("sso_supported"))],
        ["MFA Available:", _format_answer(answers.get("mfa_available"))],
        ["Encryption (Transit):", _format_answer(answers.get("encryption_transit"))],
        ["Encryption (Rest):", _format_answer(answers.get("encryption_rest"))],
        ["Audit Logs:", _format_answer(answers.get("audit_logs_available"))],
    ]
    summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(summary_table)

    story.append(Spacer(1, 20))

    # Sharing & Secondary Use
    story.append(Paragraph("Sharing & Secondary Use", heading_style))
    sharing_data = [
        ["Third-Party Sharing:", _format_answer(answers.get("third_party_sharing"))],
        ["Used for Advertising:", _format_answer(answers.get("used_for_advertising"))],
        ["Used for AI Training:", _format_answer(answers.get("used_for_ai_training"))],
        ["Data Sold:", _format_answer(answers.get("data_sold"))],
    ]
    sharing_table = Table(sharing_data, colWidths=[2*inch, 4*inch])
    sharing_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(sharing_table)

    # Footer
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated by Student Data Risk Mapper. "
        "This assessment is based on information provided and should be verified.",
        small_style
    ))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def _format_answer(value: str) -> str:
    """Format an answer value for display."""
    if not value or value == "unknown":
        return "Unknown"
    return value.replace("_", " ").title()
