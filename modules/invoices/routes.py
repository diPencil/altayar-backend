from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session
import os
import logging

from database.base import get_db
from modules.invoices.service import InvoiceService, INVOICE_STORAGE_DIR
from modules.orders.models import Order
from modules.users.models import User
from shared.dependencies import get_current_user, get_admin_user
from shared.exceptions import NotFoundException

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{order_id}/invoice")
def get_invoice(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get invoice data for an order (JSON).
    
    Requires: Bearer token
    - Customers can only access their own orders
    - Admins can access any order
    """
    # Check order ownership
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order not found")
    
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role == "CUSTOMER" and str(order.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own orders"
        )
    
    invoice_service = InvoiceService(db)
    invoice_data = invoice_service.get_invoice_data(order_id)
    
    return invoice_data


@router.get("/{order_id}/invoice/download")
def download_invoice(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate and download PDF invoice for an order.
    
    Requires: Bearer token
    - Customers can only download their own orders
    - Admins can download any order
    
    Returns: PDF file
    """
    # Check order ownership
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order not found")
    
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role == "CUSTOMER" and str(order.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only download your own invoices"
        )
    
    invoice_service = InvoiceService(db)
    pdf_bytes, _ = invoice_service.generate_invoice_pdf(order_id, save_to_file=True)
    
    filename = f"Invoice_{order.order_number}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/download/{filename}")
def download_invoice_by_filename(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download a previously generated invoice by filename.
    
    Requires: Bearer token
    """
    # Security: Only allow PDF files from the invoice storage directory
    if not filename.endswith('.pdf') or '..' in filename or '/' in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    file_path = os.path.join(INVOICE_STORAGE_DIR, filename)
    
    if not os.path.exists(file_path):
        raise NotFoundException("Invoice file not found")
    
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )


@router.get("/{order_id}/invoice/base64")
def get_invoice_base64(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get invoice as base64 encoded PDF.
    
    Useful for mobile apps that want to display inline.
    
    Requires: Bearer token
    """
    # Check order ownership
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order not found")
    
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role == "CUSTOMER" and str(order.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own invoices"
        )
    
    invoice_service = InvoiceService(db)
    base64_pdf = invoice_service.get_invoice_as_base64(order_id)
    
    return {
        "order_number": order.order_number,
        "pdf_base64": base64_pdf,
        "mime_type": "application/pdf"
    }
