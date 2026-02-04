from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import qrcode
import base64
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

# Try to register Arabic font (optional)
try:
    # You can add Arabic font support here if needed
    pass
except:
    pass


class InvoicePDFGenerator:
    """
    Generate professional PDF invoices for orders.
    
    Features:
    - Bilingual support (Arabic/English)
    - QR code with invoice reference
    - VAT breakdown
    - Professional layout
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            fontSize=24,
            spaceAfter=20,
            alignment=1  # Center
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontSize=12,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='SmallText',
            fontSize=8,
            textColor=colors.gray
        ))
    
    def generate_invoice_pdf(self, invoice_data: Dict[str, Any]) -> bytes:
        """
        Generate PDF invoice from order data.
        
        Args:
            invoice_data: Dict containing order, items, customer info
        
        Returns:
            PDF bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        story = []
        
        # Header
        story.extend(self._build_header(invoice_data))
        
        # Customer Info
        story.extend(self._build_customer_section(invoice_data))
        
        # Items Table
        story.extend(self._build_items_table(invoice_data))
        
        # Totals
        story.extend(self._build_totals_section(invoice_data))
        
        # QR Code
        story.extend(self._build_qr_section(invoice_data))
        
        # Footer
        story.extend(self._build_footer(invoice_data))
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _build_header(self, data: Dict) -> list:
        """Build invoice header"""
        elements = []
        
        # Company Name
        elements.append(Paragraph("AltayarVIP", self.styles['InvoiceTitle']))
        elements.append(Paragraph("Tourism & Travel Services", self.styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Invoice Number and Date
        invoice_info = [
            ["Invoice Number:", data.get('order_number', 'N/A')],
            ["Date:", data.get('created_at', datetime.now().strftime('%Y-%m-%d'))],
            ["Status:", data.get('payment_status', 'UNPAID')],
        ]
        
        if data.get('due_date'):
            invoice_info.append(["Due Date:", data.get('due_date')])
        
        table = Table(invoice_info, colWidths=[80, 200])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_customer_section(self, data: Dict) -> list:
        """Build customer information section"""
        elements = []
        
        elements.append(Paragraph("Bill To:", self.styles['SectionHeader']))
        
        customer = data.get('customer', {})
        customer_info = f"""
        {customer.get('first_name', '')} {customer.get('last_name', '')}<br/>
        {customer.get('email', '')}<br/>
        {customer.get('phone', '') or ''}
        """
        elements.append(Paragraph(customer_info, self.styles['Normal']))
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_items_table(self, data: Dict) -> list:
        """Build items table"""
        elements = []
        
        # Table headers
        table_data = [
            ['#', 'Description', 'Qty', 'Unit Price', 'Total']
        ]
        
        # Items
        items = data.get('items', [])
        for idx, item in enumerate(items, 1):
            table_data.append([
                str(idx),
                item.get('description_en', 'Item'),
                str(item.get('quantity', 1)),
                f"{item.get('unit_price', 0):.2f} {data.get('currency', 'USD')}",
                f"{item.get('total_price', 0):.2f} {data.get('currency', 'USD')}"
            ])
        
        table = Table(table_data, colWidths=[30, 220, 50, 80, 80])
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Body style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # # column
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),   # Numbers right-aligned
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            
            # Padding
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_totals_section(self, data: Dict) -> list:
        """Build totals section with VAT breakdown"""
        elements = []
        
        currency = data.get('currency', 'USD')
        subtotal = data.get('subtotal', 0)
        tax_amount = data.get('tax_amount', 0)
        discount = data.get('discount_amount', 0)
        total = data.get('total_amount', 0)
        
        totals_data = [
            ['Subtotal:', f"{subtotal:.2f} {currency}"],
            ['VAT (14%):', f"{tax_amount:.2f} {currency}"],
        ]
        
        if discount > 0:
            totals_data.append(['Discount:', f"-{discount:.2f} {currency}"])
        
        totals_data.append(['TOTAL:', f"{total:.2f} {currency}"])
        
        table = Table(totals_data, colWidths=[350, 110])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        return elements
    
    def _build_qr_section(self, data: Dict) -> list:
        """Build QR code section with invoice reference"""
        elements = []
        
        # Generate QR code with invoice reference
        qr_data = f"INVOICE:{data.get('order_number', 'N/A')}|AMOUNT:{data.get('total_amount', 0)}|DATE:{data.get('created_at', '')}"
        
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Add to PDF
        img = Image(qr_buffer, width=60, height=60)
        
        qr_table = Table(
            [[img, Paragraph(f"Scan to verify invoice<br/>Ref: {data.get('order_number', 'N/A')}", self.styles['SmallText'])]],
            colWidths=[70, 200]
        )
        qr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(qr_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_footer(self, data: Dict) -> list:
        """Build invoice footer"""
        elements = []
        
        footer_text = """
        Thank you for choosing AltayarVIP!<br/>
        For inquiries, contact us at support@altayarvip.com<br/>
        <br/>
        This is a computer-generated invoice and does not require a signature.
        """
        elements.append(Paragraph(footer_text, self.styles['SmallText']))
        
        return elements
