"""Translation routes."""
import uuid
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.models.schemas import (
    TranslationRequest, TranslationResponse, TranslationStatus, PDFContent
)
from app.core.translation_processor import TranslationProcessor
from app.core.pdf_exporter import export_bilingual_pdf

router = APIRouter(prefix="/api/translate", tags=["Translation"])

# Store active translation tasks
# In production, use Redis or database
translation_tasks: Dict[str, TranslationProcessor] = {}

# Use absolute path — must match pdf.py's UPLOAD_DIR
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = _BACKEND_ROOT / "uploads"
UPLOAD_DIR_FALLBACK = _BACKEND_ROOT.parent / "uploads"
OUTPUTS_DIR = _BACKEND_ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_upload(file_path: Path) -> Path:
    """Return the actual path of an uploaded file, checking both dirs."""
    if file_path.exists():
        return file_path
    fallback = UPLOAD_DIR_FALLBACK / file_path.name
    if fallback.exists():
        return fallback
    return file_path


@router.post("", response_model=TranslationResponse)
async def start_translation(
    request: TranslationRequest,
    background_tasks: BackgroundTasks
):
    """Start a new translation task.
    
    Args:
        request: Translation request
        background_tasks: FastAPI background tasks
        
    Returns:
        Translation task response
    """
    file_path = _resolve_upload(UPLOAD_DIR / f"{request.file_id}.pdf")
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "4041",
                "message": "文件不存在或已过期"
            }
        )
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    try:
        # Create translation processor
        processor = TranslationProcessor(
            file_path=str(file_path),
            provider=request.provider,
            api_key=request.api_key,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
        # Store task
        translation_tasks[task_id] = processor
        
        # Start translation in background
        background_tasks.add_task(run_translation, task_id)
        
        return TranslationResponse(
            task_id=task_id,
            status=TranslationStatus.PENDING,
            progress=0.0,
            message="翻译任务已创建"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "4005",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "5003",
                "message": f"创建翻译任务失败: {str(e)}"
            }
        )


async def run_translation(task_id: str):
    """Run translation task in background.
    
    Args:
        task_id: Task identifier
    """
    processor = translation_tasks.get(task_id)
    if not processor:
        return
    
    try:
        await processor.process()
    except Exception as e:
        print(f"Translation task {task_id} failed: {e}")
    finally:
        # Clean up after some time (e.g., 1 hour)
        # In production, use a scheduled job
        pass


@router.get("/{task_id}/status", response_model=TranslationResponse)
async def get_translation_status(task_id: str):
    """Get translation task status.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Translation status
    """
    processor = translation_tasks.get(task_id)
    
    if not processor:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "4042",
                "message": "翻译任务不存在"
            }
        )
    
    status = processor.get_status()
    
    # Prepare result if completed
    result = None
    if processor.status == TranslationStatus.COMPLETED and processor.result:
        result = {
            "file_id": processor.result.file_id,
            "filename": processor.result.filename,
            "page_count": processor.result.page_count,
        }
    
    return TranslationResponse(
        task_id=task_id,
        status=TranslationStatus(status["status"]),
        progress=status["progress"],
        message=status["message"],
        result=result
    )


@router.get("/{task_id}/result")
async def get_translation_result(task_id: str):
    """Get translation result.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Translation result pages
    """
    processor = translation_tasks.get(task_id)
    
    if not processor:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "4042",
                "message": "翻译任务不存在"
            }
        )
    
    if processor.status != TranslationStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "4006",
                "message": "翻译尚未完成"
            }
        )
    
    if not processor.result:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "5004",
                "message": "翻译结果不存在"
            }
        )
    
    # Convert to dict for JSON response
    return {
        "file_id": processor.result.file_id,
        "filename": processor.result.filename,
        "page_count": processor.result.page_count,
        "pages": [
            {
                "page_number": page.page_number,
                "text_blocks": [
                    {
                        "text": block.text,
                        "bbox": block.bbox,
                        "font_size": block.font_size,
                        "is_bold": block.is_bold,
                        "is_italic": block.is_italic,
                        "block_type": block.block_type
                    }
                    for block in page.text_blocks
                ],
                "translated_blocks": [
                    {
                        "text": block.text,
                        "bbox": block.bbox,
                        "font_size": block.font_size,
                        "is_bold": block.is_bold,
                        "is_italic": block.is_italic,
                        "block_type": block.block_type
                    }
                    for block in page.translated_blocks
                ],
                "formulas": [
                    {"content": f.content, "position": f.position}
                    for f in page.formulas
                ]
            }
            for page in processor.result.pages
        ]
    }


@router.post("/{task_id}/cancel")
async def cancel_translation(task_id: str):
    """Cancel a translation task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Cancellation status
    """
    processor = translation_tasks.get(task_id)
    
    if not processor:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "4042",
                "message": "翻译任务不存在"
            }
        )
    
    processor.cancel()
    
    return {
        "status": "cancelled",
        "task_id": task_id
    }


@router.delete("/{task_id}")
async def delete_translation(task_id: str):
    """Delete a translation task and clean up resources.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Deletion status
    """
    processor = translation_tasks.pop(task_id, None)
    
    if processor:
        processor.cancel()
        processor.close()
    
    return {
        "status": "deleted",
        "task_id": task_id
    }


@router.get("/{task_id}/export/pdf")
async def export_translated_pdf(task_id: str):
    """Export the translated PDF with bilingual annotations.

    Overlays translated text on the original PDF and returns the file
    as a downloadable attachment.

    Args:
        task_id: Translation task identifier

    Returns:
        PDF file download
    """
    processor = translation_tasks.get(task_id)

    if not processor:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "4042",
                "message": "翻译任务不存在"
            }
        )

    if processor.status != TranslationStatus.COMPLETED or not processor.result:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "4006",
                "message": "翻译尚未完成，无法导出"
            }
        )

    # Locate the source PDF
    file_id = processor.result.file_id
    source_path = _resolve_upload(UPLOAD_DIR / f"{file_id}.pdf")
    if not source_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "4041",
                "message": "原始PDF文件不存在，请重新上传"
            }
        )

    # Build the output path
    output_filename = f"{source_path.stem}_translated.pdf"
    output_path = OUTPUTS_DIR / output_filename

    try:
        # Collect pages data for the exporter
        pages_data = [
            {
                "page_number": page.page_number,
                "translated_blocks": [
                    {
                        "text": b.text,
                        "bbox": b.bbox,
                        "font_size": b.font_size,
                        "block_type": b.block_type,
                    }
                    for b in page.translated_blocks
                ],
            }
            for page in processor.result.pages
        ]

        file_size = export_bilingual_pdf(
            source_pdf_path=str(source_path),
            pages_data=pages_data,
            output_path=str(output_path),
        )

        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename=output_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
                "Content-Length": str(file_size),
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "5005",
                "message": f"PDF导出失败: {str(e)}"
            }
        )
