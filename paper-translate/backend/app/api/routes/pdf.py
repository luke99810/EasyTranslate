"""PDF upload and management routes."""
import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from app.models.schemas import FileUploadResponse, ErrorResponse
from app.core.pdf_processor import PDFProcessor

router = APIRouter(prefix="/api/pdf", tags=["PDF"])

# Configuration — use absolute path so uploads survive cwd changes
# The "primary" dir is backend/uploads (4 levels up from this file).
# A fallback dir (paper-translate/uploads) is also checked when reading.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = _BACKEND_ROOT / "uploads"
UPLOAD_DIR_FALLBACK = _BACKEND_ROOT.parent / "uploads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf"}

# Ensure upload directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR_FALLBACK.mkdir(parents=True, exist_ok=True)


def _resolve_upload(file_path: Path) -> Path:
    """Return the actual path of an uploaded file, checking both dirs."""
    if file_path.exists():
        return file_path
    fallback = UPLOAD_DIR_FALLBACK / file_path.name
    if fallback.exists():
        return fallback
    return file_path  # will 404 downstream — that's fine


@router.post("/upload", response_model=FileUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file.

    Only saves the file to disk — no PDF parsing here.
    Parsing is deferred to /{file_id}/info so the upload response
    returns instantly even for large or complex PDFs.
    
    Args:
        file: PDF file to upload
        
    Returns:
        File upload response with file ID (page_count may be 0 until /info is called)
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "4001",
                "message": "仅支持PDF格式文件"
            }
        )
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}.pdf"
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            file_path.unlink()  # Delete oversized file
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "4002",
                    "message": f"文件大小超过限制（最大{MAX_FILE_SIZE // 1024 // 1024}MB）"
                }
            )
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            page_count=0,  # Will be filled after /info call
            file_size=file_size,
            status="uploaded"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "5001",
                "message": f"文件上传失败: {str(e)}"
            }
        )


@router.get("/{file_id}/info")
async def get_pdf_info(file_id: str):
    """Get PDF file information (parses the PDF).

    This endpoint actually opens the PDF with PyMuPDF to extract
    page count and metadata. Called separately after upload so that
    the upload itself stays fast.
    
    Args:
        file_id: File identifier
        
    Returns:
        PDF information including page_count and validation status
    """
    file_path = _resolve_upload(UPLOAD_DIR / f"{file_id}.pdf")
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "4041",
                "message": "文件不存在或已过期"
            }
        )
    
    try:
        with PDFProcessor(str(file_path)) as processor:
            info = processor.get_info()
            page_count = info["page_count"]
            
            # Validate page count
            if page_count > 100:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "4003",
                        "message": "PDF页数超过限制（最大100页）"
                    }
                )
            
            return {
                "file_id": file_id,
                "page_count": page_count,
                "metadata": info.get("metadata", {}),
                "status": "ready"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "5002",
                "message": f"无法解析PDF文件: {str(e)}"
            }
        )


@router.delete("/{file_id}")
async def delete_pdf(file_id: str):
    """Delete uploaded PDF file.
    
    Args:
        file_id: File identifier
        
    Returns:
        Deletion status
    """
    file_path = _resolve_upload(UPLOAD_DIR / f"{file_id}.pdf")
    
    if file_path.exists():
        file_path.unlink()
    
    return {"status": "deleted", "file_id": file_id}


@router.get("/{file_id}/serve")
async def serve_pdf(file_id: str):
    """Serve the PDF file for frontend rendering (pdf.js).

    Returns the raw PDF binary so pdf.js can render it client-side.

    Args:
        file_id: File identifier

    Returns:
        PDF file binary
    """
    file_path = _resolve_upload(UPLOAD_DIR / f"{file_id}.pdf")

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "4041",
                "message": "文件不存在或已过期"
            }
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
        headers={"Cache-Control": "public, max-age=3600"}
    )
