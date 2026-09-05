import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_recovery_report_pdf(report_data: dict) -> bytes:
    """
    Generates a professional PDF report based on recovery metrics.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#1e293b"),
        alignment=TA_CENTER,
        spaceAfter=20
    )

    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=30
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=20,
        spaceAfter=12
    )

    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=10
    )

    elements = []

    # --- HEADER ---
    elements.append(Paragraph("VASOOLI", title_style))
    elements.append(Paragraph("Recovery Batch Compliance Report", subtitle_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=9, textColor=colors.grey)))
    elements.append(Spacer(1, 0.2 * inch))

    # --- EXECUTIVE SUMMARY ---
    elements.append(Paragraph("Executive Summary", section_header_style))

    # Summary Table
    summary_data = [
        ["Metric", "Value"],
        ["Records Processed", f"{report_data['records_processed']}"],
        ["Total Amount at Risk", f"₹{report_data['total_at_risk_inr']:,.2f}"],
        ["Total Amount Recovered", f"₹{report_data['total_recovered_inr']:,.2f}"],
        ["Recovery Rate", f"{report_data['recovery_rate_pct']}%"],
        ["Total Channel Cost", f"₹{report_data['total_channel_cost_inr']:,.2f}"],
    ]

    summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # --- FUNNEL BY TIER ---
    elements.append(Paragraph("Recovery Funnel by Tier", section_header_style))

    funnel_header = ["Tier", "Count", "Recovered Amount"]
    funnel_rows = []
    for tier, stats in report_data['funnel_by_tier'].items():
        funnel_rows.append([tier, str(stats['count']), f"₹{stats['recovered_inr']:,.2f}"])

    funnel_table = Table([funnel_header] + funnel_rows, colWidths=[2 * inch, 1 * inch, 2 * inch])
    funnel_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(funnel_table)
    elements.append(Spacer(1, 0.3 * inch))

    # --- EXCEPTIONS ---
    elements.append(Paragraph("Unresolved Records (Exceptions)", section_header_style))
    if not report_data['exceptions_sample']:
        elements.append(Paragraph("No unresolved records found in this batch.", body_style))
    else:
        ex_header = ["Record ID", "Merchant", "Amount", "Cause"]
        ex_rows = []
        for e in report_data['exceptions_sample']:
            ex_rows.append([e['record_id'], e['merchant_id'], f"₹{e['amount_inr']:,.0f}", e['root_cause']])

        ex_table = Table([ex_header] + ex_rows, colWidths=[1.5 * inch, 1.5 * inch, 1 * inch, 2 * inch])
        ex_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fef2f2")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.red),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(ex_table)

    # --- COMPLIANCE FOOTER ---
    elements.append(Spacer(1, 1 * inch))
    elements.append(Paragraph("Compliance Statement", section_header_style))
    compliance_text = (
        "This recovery report was generated by the Vasooli Decision Layer. All interventions "
        "followed structural compliance guardrails: the NPCI 3-retry ceiling was strictly "
        "enforced, and DND/Consent flags were verified before any active outreach. No "
        "interventions were made outside of these hard-coded boundaries."
    )
    elements.append(Paragraph(compliance_text, ParagraphStyle('Compliance', parent=styles['Normal'], fontSize=9, textColor=colors.grey, italic=True)))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
