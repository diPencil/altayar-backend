from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import os
import uuid
import base64
import logging

from modules.invoices.pdf_generator import InvoicePDFGenerator
from modules.orders.models import Order
from modules.users.models import User
from shared.exceptions import NotFoundException
from config.settings import settings

logger = logging.getLogger(__name__)

# Directory for storing generated PDFs
INVOICE_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'storage', 'invoices')
os.makedirs(INVOICE_STORAGE_DIR, exist_ok=True)


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.pdf_generator = InvoicePDFGenerator()
    
    def get_invoice_data(self, order_id: str) -> Dict[str, Any]:
        """
        Get all data needed for invoice generation.
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise NotFoundException("Order not found")
        
        # Get customer
        customer = self.db.query(User).filter(User.id == order.user_id).first()
        
        # Build invoice data
        invoice_data = {
            'order_id': str(order.id),
            'order_number': order.order_number,
            'order_type': order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
            'status': order.status.value if hasattr(order.status, 'value') else str(order.status),
            'payment_status': order.payment_status.value if hasattr(order.payment_status, 'value') else str(order.payment_status),
            'subtotal': float(order.subtotal),
            'tax_amount': float(order.tax_amount),
            'discount_amount': float(order.discount_amount or 0),
            'total_amount': float(order.total_amount),
            'currency': order.currency,
            'notes_en': order.notes_en,
            'notes_ar': order.notes_ar,
            'created_at': order.created_at.strftime('%Y-%m-%d') if order.created_at else datetime.now().strftime('%Y-%m-%d'),
            'due_date': order.due_date.strftime('%Y-%m-%d') if order.due_date else None,
            'issued_at': order.issued_at.strftime('%Y-%m-%d %H:%M') if order.issued_at else None,
            'paid_at': order.paid_at.strftime('%Y-%m-%d %H:%M') if order.paid_at else None,
            'customer': {
                'id': str(customer.id) if customer else None,
                'first_name': customer.first_name if customer else 'N/A',
                'last_name': customer.last_name if customer else '',
                'email': customer.email if customer else 'N/A',
                'phone': customer.phone if customer else None,
            },
            'items': []
        }
        
        # Add items
        for item in order.items:
            invoice_data['items'].append({
                'description_ar': item.description_ar,
                'description_en': item.description_en,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price),
            })
        
        return invoice_data
    
    def generate_invoice_pdf(self, order_id: str, save_to_file: bool = True) -> tuple[bytes, str]:
        """
        Generate PDF invoice for an order.
        
        Args:
            order_id: Order ID
            save_to_file: Whether to save PDF to file system
        
        Returns:
            (pdf_bytes, file_path or None)
        """
        invoice_data = self.get_invoice_data(order_id)
        
        # Generate PDF
        pdf_bytes = self.pdf_generator.generate_invoice_pdf(invoice_data)
        
        file_path = None
        if save_to_file:
            # Generate unique filename
            filename = f"{invoice_data['order_number']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            file_path = os.path.join(INVOICE_STORAGE_DIR, filename)
            
            # Save to file
            with open(file_path, 'wb') as f:
                f.write(pdf_bytes)
            
            logger.info(f"✅ Invoice PDF generated: {file_path}")
        
        return pdf_bytes, file_path
    
    def get_invoice_as_base64(self, order_id: str) -> str:
        """
        Generate invoice and return as base64 string.
        Useful for API responses when file storage isn't desired.
        """
        pdf_bytes, _ = self.generate_invoice_pdf(order_id, save_to_file=False)
        return base64.b64encode(pdf_bytes).decode('utf-8')
    
    def get_invoice_url(self, order_id: str) -> str:
        """
        Generate invoice and return download URL.
        """
        _, file_path = self.generate_invoice_pdf(order_id, save_to_file=True)
        
        # Return relative URL for download endpoint
        filename = os.path.basename(file_path)
        return f"/api/invoices/download/{filename}"
