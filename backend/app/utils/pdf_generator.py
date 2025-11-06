"""
PDF Generation Utilities
PDF 생성 유틸리티

Uses ReportLab to generate PDF documents from conversation and report data.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class PDFGenerator:
    """PDF document generator using ReportLab"""

    def __init__(self):
        """Initialize PDF generator with Korean font support"""
        self.styles = getSampleStyleSheet()

        # Try to register Korean font (NanumGothic)
        # If not available, fall back to built-in fonts
        try:
            # TODO: Add Korean font file to project
            # pdfmetrics.registerFont(TTFont('NanumGothic', 'NanumGothic.ttf'))
            # self.korean_font = 'NanumGothic'
            self.korean_font = 'Helvetica'  # Fallback
        except:
            self.korean_font = 'Helvetica'

        # Create custom styles
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=self.korean_font,
        ))

        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            fontName=self.korean_font,
        ))

        # Subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubheading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            fontName=self.korean_font,
        ))

        # Body style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_JUSTIFY,
            fontName=self.korean_font,
        ))

        # Message style
        self.styles.add(ParagraphStyle(
            name='UserMessage',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#2980b9'),
            leftIndent=20,
            fontName=self.korean_font,
        ))

        self.styles.add(ParagraphStyle(
            name='AssistantMessage',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#27ae60'),
            leftIndent=20,
            fontName=self.korean_font,
        ))

    def generate_conversation_pdf(self, data: Dict[str, Any]) -> bytes:
        """
        Generate PDF from conversation data

        Args:
            data: Conversation export data dictionary

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        # Build PDF content
        story = []

        # Title
        conversation = data['conversation']
        title = conversation.get('title', 'Conversation Export')
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 0.5*cm))

        # Metadata section
        if data.get('metadata'):
            story.append(Paragraph("Conversation Information", self.styles['CustomHeading']))

            metadata_table_data = [
                ['Created', conversation['created_at']],
                ['Last Updated', conversation['updated_at']],
                ['Status', conversation.get('status', 'N/A')],
            ]

            if data['metadata'].get('crisis_detected'):
                metadata_table_data.append(
                    ['⚠️ Crisis Detected', f"Level {data['metadata']['crisis_severity']}"]
                )

            metadata_table = Table(metadata_table_data, colWidths=[4*cm, 12*cm])
            metadata_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(metadata_table)
            story.append(Spacer(1, 1*cm))

        # Messages section
        story.append(Paragraph("Conversation Messages", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.3*cm))

        messages = data.get('messages', [])
        for i, msg in enumerate(messages):
            # Message header (role and timestamp)
            role = msg['role'].capitalize()
            timestamp = msg['created_at'][:19].replace('T', ' ')

            header_text = f"<b>{role}</b> - {timestamp}"
            story.append(Paragraph(header_text, self.styles['CustomBody']))
            story.append(Spacer(1, 0.1*cm))

            # Message content
            content = msg['content'].replace('\n', '<br/>')
            if msg['role'] == 'user':
                style = self.styles['UserMessage']
            else:
                style = self.styles['AssistantMessage']

            story.append(Paragraph(content, style))

            # Crisis keywords if present
            if msg.get('contains_crisis_keywords') and msg.get('detected_keywords'):
                keywords = ', '.join(msg['detected_keywords'])
                warning = f"<font color='red'>⚠️ Crisis Keywords: {keywords}</font>"
                story.append(Spacer(1, 0.1*cm))
                story.append(Paragraph(warning, self.styles['CustomBody']))

            story.append(Spacer(1, 0.5*cm))

            # Page break every 10 messages for better readability
            if (i + 1) % 10 == 0 and i < len(messages) - 1:
                story.append(PageBreak())

        # Statistics section
        if data.get('statistics'):
            story.append(PageBreak())
            story.append(Paragraph("Statistics", self.styles['CustomHeading']))
            story.append(Spacer(1, 0.3*cm))

            stats = data['statistics']
            stats_table_data = [
                ['Total Messages', str(stats['total_messages'])],
                ['User Messages', str(stats['user_messages'])],
                ['Assistant Messages', str(stats['assistant_messages'])],
                ['Crisis Messages', str(stats['crisis_messages'])],
            ]

            stats_table = Table(stats_table_data, colWidths=[8*cm, 8*cm])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498db')),
                ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ]))
            story.append(stats_table)

        # Footer
        story.append(Spacer(1, 1*cm))
        footer_text = f"<i>Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"
        story.append(Paragraph(footer_text, self.styles['CustomBody']))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def generate_progress_report_pdf(self, data: Dict[str, Any]) -> bytes:
        """
        Generate PDF progress report

        Args:
            data: Progress report data dictionary

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        story = []

        # Title
        story.append(Paragraph("Progress Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.3*cm))

        # Report period
        report_info = data['report_info']
        date_range = report_info['date_range']
        period_text = f"Period: {date_range['from'][:10]} to {date_range['to'][:10]}"
        story.append(Paragraph(period_text, self.styles['CustomBody']))
        story.append(Spacer(1, 0.8*cm))

        # User information
        if data.get('user_info'):
            story.append(Paragraph("User Information", self.styles['CustomHeading']))
            user_info = data['user_info']

            user_table_data = [
                ['User ID', user_info['user_id'][:8] + '...'],
                ['Member Since', user_info['created_at'][:10]],
                ['Last Active', user_info['last_active'][:10]],
            ]

            user_table = Table(user_table_data, colWidths=[6*cm, 10*cm])
            user_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(user_table)
            story.append(Spacer(1, 1*cm))

        # Statistics
        if data.get('statistics'):
            story.append(Paragraph("Activity Statistics", self.styles['CustomHeading']))
            stats = data['statistics']

            stats_table_data = [
                ['Metric', 'Count'],
                ['Conversations', str(stats.get('conversations', 0))],
                ['Messages', str(stats.get('messages', 0))],
                ['Sessions', str(stats.get('sessions', 0))],
            ]

            stats_table = Table(stats_table_data, colWidths=[10*cm, 6*cm])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 1*cm))

        # Crisis history
        if data.get('crisis_history'):
            story.append(Paragraph("Crisis Event History", self.styles['CustomHeading']))
            crisis_logs = data['crisis_history']

            if crisis_logs:
                crisis_table_data = [['Date', 'Risk Level', 'Keywords']]

                for log in crisis_logs[:10]:  # Show latest 10
                    date = log['detected_at'][:10]
                    level = str(log['risk_level'])
                    keywords = ', '.join(log.get('detected_keywords', [])[:3])  # First 3
                    crisis_table_data.append([date, level, keywords])

                crisis_table = Table(crisis_table_data, colWidths=[4*cm, 3*cm, 9*cm])
                crisis_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(crisis_table)
            else:
                story.append(Paragraph("No crisis events during this period.", self.styles['CustomBody']))

        # Footer
        story.append(Spacer(1, 2*cm))
        footer_text = f"<i>Report generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"
        story.append(Paragraph(footer_text, self.styles['CustomBody']))

        # Build PDF
        doc.build(story)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes


# Singleton instance
pdf_generator = PDFGenerator()


def generate_conversation_pdf(data: Dict[str, Any]) -> bytes:
    """Generate conversation PDF (convenience function)"""
    return pdf_generator.generate_conversation_pdf(data)


def generate_progress_report_pdf(data: Dict[str, Any]) -> bytes:
    """Generate progress report PDF (convenience function)"""
    return pdf_generator.generate_progress_report_pdf(data)
