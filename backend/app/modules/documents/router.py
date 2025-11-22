"""
Documents module - Router

Endpoints for document upload and management.
"""

from fastapi import APIRouter, Depends, UploadFile, File, status
from app.core.dependencies import TenantUser

router = APIRouter()


@router.get("/")
async def list_documents(current_user: TenantUser):
    """List all documents for current tenant."""
    # TODO: Implement
    return {"documents": [], "total": 0}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: TenantUser = Depends()
):
    """Upload a document for processing."""
    # TODO: Implement PDF processing
    return {
        "id": "placeholder",
        "filename": file.filename,
        "message": "Not implemented"
    }


@router.get("/{document_id}")
async def get_document(document_id: str, current_user: TenantUser):
    """Get document by ID."""
    # TODO: Implement
    return {"id": document_id, "message": "Not implemented"}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, current_user: TenantUser):
    """Delete document."""
    # TODO: Implement
    pass
