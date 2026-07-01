"""
PDF Export — Topshiriqni PDF formatda chiqarish (offline tarqatish uchun)
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.utils import timezone


class AssignmentPDFExporter:
    def __init__(self, assignment):
        self.assignment = assignment

    def generate(self) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=14, spaceAfter=12,
        )
        question_style = ParagraphStyle(
            'Question',
            parent=styles['Normal'],
            fontSize=11, spaceBefore=8, spaceAfter=4, leftIndent=0,
        )
        option_style = ParagraphStyle(
            'Option',
            parent=styles['Normal'],
            fontSize=10, leftIndent=20,
        )

        story = []

        # Sarlavha
        story.append(Paragraph(f"<b>{self.assignment.title}</b>", title_style))
        story.append(Paragraph(
            f"Fan: {self.assignment.subject_assignment.subject.name} | "
            f"Guruh: {self.assignment.subject_assignment.group.name} | "
            f"Muddat: {self.assignment.end_datetime.strftime('%d.%m.%Y %H:%M')}",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.5*cm))

        # Savollar
        questions = self.assignment.questions.prefetch_related('options').order_by('order_index')
        for i, question in enumerate(questions, start=1):
            story.append(Paragraph(f"<b>{i}. {question.question_text}</b> ({question.points} ball)", question_style))
            for opt in question.options.order_by('order_index'):
                story.append(Paragraph(f"○  {opt.option_text}", option_style))
            story.append(Spacer(1, 0.3*cm))

        # Imzo joyi
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            f"Talaba F.I.Sh.: ____________________________  "
            f"Imzo: ____________  "
            f"Sana: {timezone.now().strftime('%d.%m.%Y')}",
            styles['Normal']
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer
