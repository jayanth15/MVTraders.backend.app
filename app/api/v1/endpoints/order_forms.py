"""
Order form management endpoints for vendor-customizable order forms.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models.order_form import OrderForm, FormSubmission, FormFieldSchema
from app.models.vendor import Vendor
from app.models.user import User
from app.models.order import Order
from app.core.deps import get_current_user
from datetime import datetime
import json

router = APIRouter()


@router.post("/", response_model=OrderForm, status_code=status.HTTP_201_CREATED)
async def create_order_form(
    form_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new order form (vendor only)."""
    
    # Check if user is a vendor
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vendors can create order forms"
        )
    
    # Validate form fields
    fields = form_data.get("fields", [])
    validated_fields = []
    
    for field in fields:
        try:
            # Validate field schema
            field_schema = FormFieldSchema(**field)
            validated_fields.append(field_schema.dict())
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field schema: {str(e)}"
            )
    
    # Create order form
    order_form = OrderForm(
        vendor_id=vendor.id,
        name=form_data["name"],
        description=form_data.get("description"),
        fields=validated_fields,
        is_active=form_data.get("is_active", True),
        submission_settings=form_data.get("submission_settings", {}),
        custom_css=form_data.get("custom_css"),
        custom_js=form_data.get("custom_js")
    )
    
    session.add(order_form)
    session.commit()
    session.refresh(order_form)
    
    return order_form


@router.get("/", response_model=List[OrderForm])
async def get_order_forms(
    vendor_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get order forms. Vendors see their own forms, customers see public forms."""
    
    query = select(OrderForm)
    
    # Check if user is a vendor
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    if vendor:
        # Vendor viewing their own forms
        query = query.where(OrderForm.vendor_id == vendor.id)
    else:
        # Customer viewing public forms
        if vendor_id:
            query = query.where(
                OrderForm.vendor_id == vendor_id,
                OrderForm.is_active == True
            )
        else:
            query = query.where(OrderForm.is_active == True)
    
    if is_active is not None:
        query = query.where(OrderForm.is_active == is_active)
    
    query = query.offset(offset).limit(limit).order_by(OrderForm.created_at.desc())
    forms = session.exec(query).all()
    
    return forms


@router.get("/{form_id}", response_model=OrderForm)
async def get_order_form(
    form_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific order form by ID."""
    
    form = session.get(OrderForm, form_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order form not found"
        )
    
    # Check access permission
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    # Vendors can see their own forms, customers can see active forms
    if vendor and form.vendor_id == vendor.id:
        return form
    elif form.is_active:
        return form
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Form is not accessible"
        )


@router.put("/{form_id}", response_model=OrderForm)
async def update_order_form(
    form_id: int,
    form_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update an order form (vendor only)."""
    
    form = session.get(OrderForm, form_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order form not found"
        )
    
    # Check if user is the vendor who owns this form
    vendor = session.exec(
        select(Vendor).where(
            Vendor.user_id == current_user.id,
            Vendor.id == form.vendor_id
        )
    ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the form owner can update this form"
        )
    
    # Validate form fields if provided
    if "fields" in form_data:
        fields = form_data["fields"]
        validated_fields = []
        
        for field in fields:
            try:
                field_schema = FormFieldSchema(**field)
                validated_fields.append(field_schema.dict())
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid field schema: {str(e)}"
                )
        
        form_data["fields"] = validated_fields
    
    # Update form
    for key, value in form_data.items():
        if key != "id" and hasattr(form, key):
            setattr(form, key, value)
    
    form.updated_at = datetime.utcnow()
    session.add(form)
    session.commit()
    session.refresh(form)
    
    return form


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_form(
    form_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete an order form (vendor only)."""
    
    form = session.get(OrderForm, form_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order form not found"
        )
    
    # Check if user is the vendor who owns this form
    vendor = session.exec(
        select(Vendor).where(
            Vendor.user_id == current_user.id,
            Vendor.id == form.vendor_id
        )
    ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the form owner can delete this form"
        )
    
    session.delete(form)
    session.commit()


@router.post("/{form_id}/submit", response_model=FormSubmission, status_code=status.HTTP_201_CREATED)
async def submit_order_form(
    form_id: int,
    submission_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Submit an order form."""
    
    form = session.get(OrderForm, form_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order form not found"
        )
    
    if not form.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form is not accepting submissions"
        )
    
    # Validate submission data against form fields
    form_fields = {field["name"]: field for field in form.fields}
    validated_data = {}
    errors = []
    
    for field_name, field_config in form_fields.items():
        field_value = submission_data.get(field_name)
        
        # Check required fields
        if field_config.get("required", False) and not field_value:
            errors.append(f"Field '{field_name}' is required")
            continue
        
        # Basic type validation
        field_type = field_config.get("type", "text")
        if field_value is not None:
            try:
                if field_type == "number":
                    validated_data[field_name] = float(field_value)
                elif field_type == "email":
                    # Basic email validation
                    if "@" not in str(field_value):
                        errors.append(f"Field '{field_name}' must be a valid email")
                    else:
                        validated_data[field_name] = str(field_value)
                else:
                    validated_data[field_name] = field_value
            except (ValueError, TypeError):
                errors.append(f"Field '{field_name}' has invalid type")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors}
        )
    
    # Create form submission
    submission = FormSubmission(
        form_id=form_id,
        user_id=current_user.id,
        data=validated_data,
        metadata={
            "user_agent": submission_data.get("_user_agent"),
            "ip_address": submission_data.get("_ip_address"),
            "submission_time": datetime.utcnow().isoformat()
        }
    )
    
    session.add(submission)
    session.commit()
    session.refresh(submission)
    
    return submission


@router.get("/{form_id}/submissions", response_model=List[FormSubmission])
async def get_form_submissions(
    form_id: int,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get submissions for a form (vendor only)."""
    
    form = session.get(OrderForm, form_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order form not found"
        )
    
    # Check if user is the vendor who owns this form
    vendor = session.exec(
        select(Vendor).where(
            Vendor.user_id == current_user.id,
            Vendor.id == form.vendor_id
        )
    ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the form owner can view submissions"
        )
    
    submissions = session.exec(
        select(FormSubmission)
        .where(FormSubmission.form_id == form_id)
        .offset(offset)
        .limit(limit)
        .order_by(FormSubmission.created_at.desc())
    ).all()
    
    return submissions


@router.get("/submissions/{submission_id}", response_model=FormSubmission)
async def get_form_submission(
    submission_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific form submission."""
    
    submission = session.get(FormSubmission, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form submission not found"
        )
    
    # Check access permission
    form = session.get(OrderForm, submission.form_id)
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    # User can see their own submission, vendor can see submissions to their forms
    if submission.user_id == current_user.id:
        return submission
    elif vendor and form and form.vendor_id == vendor.id:
        return submission
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this submission"
        )


@router.post("/submissions/{submission_id}/convert-to-order", response_model=dict)
async def convert_submission_to_order(
    submission_id: int,
    order_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Convert a form submission to an order (vendor only)."""
    
    submission = session.get(FormSubmission, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form submission not found"
        )
    
    # Check if user is the vendor
    form = session.get(OrderForm, submission.form_id)
    vendor = session.exec(
        select(Vendor).where(
            Vendor.user_id == current_user.id,
            Vendor.id == form.vendor_id
        )
    ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the form owner can convert submissions"
        )
    
    if submission.order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission has already been converted to an order"
        )
    
    # Create order based on submission and additional order data
    order_data.update({
        "vendor_id": vendor.id,
        "customer_id": submission.user_id,
        "form_submission_id": submission.id,
        "notes": f"Created from form submission #{submission.id}"
    })
    
    # Here you would typically call the order creation logic
    # For now, we'll return a placeholder
    return {
        "message": "Submission conversion initiated",
        "submission_id": submission_id,
        "vendor_id": vendor.id,
        "customer_id": submission.user_id
    }
