# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os

pdf_filename = "Test_Versicherungspolizze.pdf"
doc = SimpleDocTemplate(
    pdf_filename,
    pagesize=letter,
    rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
)

styles = getSampleStyleSheet()

# Colors
primary_color = colors.HexColor("#003366")
secondary_color = colors.HexColor("#333333")
accent_color = colors.HexColor("#e6f2ff")

# Custom Styles
title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Heading1"],
    fontSize=22,
    leading=26,
    textColor=primary_color,
    fontName="Helvetica-Bold",
    spaceAfter=6
)

subtitle_style = ParagraphStyle(
    "DocSubtitle",
    parent=styles["Heading2"],
    fontSize=14,
    leading=18,
    textColor=colors.HexColor("#0055a5"),
    fontName="Helvetica-Bold",
    spaceAfter=12
)

body_style = ParagraphStyle(
    "BodyTextCustom",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    textColor=secondary_color,
    fontName="Helvetica"
)

label_style = ParagraphStyle(
    "LabelCustom",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    textColor=colors.HexColor("#555555"),
    fontName="Helvetica-Bold"
)

value_style = ParagraphStyle(
    "ValueCustom",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    textColor=colors.black,
    fontName="Helvetica"
)

story = []

# Header Banner
story.append(Paragraph("<b>Allianz Versicherung AG</b>", title_style))
story.append(Paragraph("Königinstr. 28, 80802 München • Tel: 0800 4100 111 • E-Mail: info@allianz.de", body_style))
story.append(Spacer(1, 10))
story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceAfter=15))

# Document Title
story.append(Paragraph("VERSICHERUNGSSCHEIN / POLIZZE", subtitle_style))
story.append(Paragraph("<b>Privat-Haftpflichtversicherung Premium Plus</b>", ParagraphStyle("SubHeader", parent=styles["Normal"], fontSize=12, leading=15, textColor=colors.black, fontName="Helvetica-Bold", spaceAfter=15)))

# Key Details Table
data = [
    [Paragraph("Versicherer:", label_style), Paragraph("Allianz Versicherungs-AG", value_style)],
    [Paragraph("Versicherungsnehmer:", label_style), Paragraph("Dennis Guse", value_style)],
    [Paragraph("Versicherungsscheinnummer:", label_style), Paragraph("<b>VS-84920491-H</b>", value_style)],
    [Paragraph("Dokumentendatum:", label_style), Paragraph("15.12.2023", value_style)],
    [Paragraph("Versicherungsbeginn:", label_style), Paragraph("01.01.2024", value_style)],
    [Paragraph("Vertragsende:", label_style), Paragraph("01.01.2027", value_style)],
    [Paragraph("Kündigungsfrist:", label_style), Paragraph("3 Monate vor Ablauf (01.10.2026)", value_style)],
    [Paragraph("Jahresbeitrag:", label_style), Paragraph("148,50 EUR (inkl. Versicherungsteuer)", value_style)],
]

t = Table(data, colWidths=[180, 330])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
]))
story.append(t)
story.append(Spacer(1, 20))

# Description Section
story.append(Paragraph("<b>Vertragsgegenstand & Leistungsumfang:</b>", ParagraphStyle("SecTitle", parent=styles["Normal"], fontSize=11, leading=14, fontName="Helvetica-Bold", spaceAfter=6)))
description_text = (
    "Hiermit bestätigen wir den Abschluss der Privat-Haftpflichtversicherung für Herrn Dennis Guse. "
    "Der Versicherungsschutz umfasst Personenschäden, Sachschäden sowie Vermögensschäden bis zu einer "
    "Deckungssumme von 50.000.000 EUR pauschal. Eingeschlossen sind Schlüsselverlust, Mietsachschäden "
    "und die Nutzung von Drohnen bis 5 kg."
)
story.append(Paragraph(description_text, body_style))
story.append(Spacer(1, 15))

# Cancellation Policy Box
story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=15))
story.append(Paragraph("<b>Wichtiger Hinweis zur Kündigung:</b>", ParagraphStyle("WarnTitle", parent=styles["Normal"], fontSize=10, leading=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#990000"), spaceAfter=4)))
cancellation_text = (
    "Der Vertrag verlängert sich automatisch um ein weiteres Jahr, wenn er nicht spätestens 3 Monate vor dem "
    "jeweiligen Vertragsende (spätestens am <b>01.10.2026</b>) schriftlich gekündigt wird."
)
story.append(Paragraph(cancellation_text, body_style))
story.append(Spacer(1, 30))

# Signature block
story.append(Paragraph("München, den 15.12.2023", body_style))
story.append(Spacer(1, 10))
story.append(Paragraph("<b>Allianz Versicherungs-AG</b><br/><font color='#777777'>Vorstand & Vertretung</font>", body_style))

doc.build(story)
print(f"PDF successfully generated: {os.path.abspath(pdf_filename)}")
