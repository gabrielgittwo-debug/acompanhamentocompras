import os
import tempfile
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from sqlalchemy import func
from models import AcquisitionType, AcquisitionStatus
from app import db

def generate_report_pdf(acquisitions):
    """Generate a professional PDF report with acquisition data"""
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.close()
    
    # Create document
    doc = SimpleDocTemplate(
        temp_file.name,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Container for the 'Flowable' objects
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.HexColor('#1e4a6b'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.HexColor('#1e4a6b'),
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#1e4a6b'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    # Header
    story.append(Paragraph("SENAI Morvan Figueiredo", title_style))
    story.append(Paragraph("Sistema de Acompanhamento de Aquisições", header_style))
    story.append(Paragraph(f"Relatório Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", header_style))
    story.append(Spacer(1, 20))
    
    # Summary Statistics
    story.append(Paragraph("Resumo Executivo", subtitle_style))
    
    total_acquisitions = len(acquisitions)
    servicos_count = len([a for a in acquisitions if a.type == AcquisitionType.SERVICO])
    insumos_count = len([a for a in acquisitions if a.type == AcquisitionType.INSUMO])
    
    total_value = sum([a.final_value or 0 for a in acquisitions])
    servicos_value = sum([a.final_value or 0 for a in acquisitions if a.type == AcquisitionType.SERVICO])
    insumos_value = sum([a.final_value or 0 for a in acquisitions if a.type == AcquisitionType.INSUMO])
    
    summary_data = [
        ['Indicador', 'Quantidade', 'Valor (R$)'],
        ['Total de Solicitações', str(total_acquisitions), f'R$ {total_value:,.2f}'],
        ['Serviços', str(servicos_count), f'R$ {servicos_value:,.2f}'],
        ['Insumos', str(insumos_count), f'R$ {insumos_value:,.2f}'],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e4a6b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 30))
    
    # Status Distribution
    story.append(Paragraph("Distribuição por Status", subtitle_style))
    
    status_counts = {}
    for acquisition in acquisitions:
        status = acquisition.status_display
        status_counts[status] = status_counts.get(status, 0) + 1
    
    status_data = [['Status', 'Quantidade', 'Percentual']]
    for status, count in status_counts.items():
        percentage = (count / total_acquisitions) * 100 if total_acquisitions > 0 else 0
        status_data.append([status, str(count), f'{percentage:.1f}%'])
    
    status_table = Table(status_data, colWidths=[2.5*inch, 1*inch, 1*inch])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e4a6b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    story.append(status_table)
    story.append(PageBreak())
    
    # Detailed Acquisitions List
    story.append(Paragraph("Detalhamento das Solicitações", subtitle_style))
    
    # Table headers
    detailed_data = [
        ['ID', 'Título', 'Tipo', 'Status', 'Solicitante', 'Valor', 'Data']
    ]
    
    for acquisition in acquisitions[:50]:  # Limit to first 50 for readability
        detailed_data.append([
            str(acquisition.id),
            acquisition.title[:30] + ('...' if len(acquisition.title) > 30 else ''),
            acquisition.type_display,
            acquisition.status_display,
            acquisition.requester.full_name[:20] + ('...' if len(acquisition.requester.full_name) > 20 else ''),
            f'R$ {acquisition.final_value:,.2f}' if acquisition.final_value else 'N/A',
            acquisition.created_at.strftime('%d/%m/%Y')
        ])
    
    detailed_table = Table(detailed_data, colWidths=[0.5*inch, 1.5*inch, 0.8*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch])
    detailed_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e4a6b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(detailed_table)
    
    # Add note if more than 50 acquisitions
    if len(acquisitions) > 50:
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<i>Mostrando as primeiras 50 solicitações de um total de {len(acquisitions)}.</i>", 
                             styles['Normal']))
    
    # Footer
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Paragraph("Relatório gerado pelo Sistema de Acompanhamento de Aquisições - SENAI Morvan Figueiredo", 
                         footer_style))
    
    # Build PDF
    doc.build(story)
    
    return temp_file.name
