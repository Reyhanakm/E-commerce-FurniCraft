from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib import colors

def get_invoice_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="DejaVuSans",
        fontSize=20,
        spaceAfter=20,
    )

    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="DejaVuSans",
        fontSize=10,
        textColor=colors.grey,
    )

    value_style = ParagraphStyle(
        "ValueStyle",
        parent=styles["Normal"],
        fontName="DejaVuSans",
        fontSize=11,
    )

    bold_style = ParagraphStyle(
        "BoldStyle",
        parent=styles["Normal"],
        fontName="DejaVuSans",
        fontSize=11,
    )

    right_style = ParagraphStyle(
        "RightStyle",
        fontName="DejaVuSans",
        parent=styles["Normal"],
        alignment=TA_RIGHT,
    )

    return {
        "title": title_style,
        "label": label_style,
        "value": value_style,
        "bold": bold_style,
        "right": right_style,
    }
