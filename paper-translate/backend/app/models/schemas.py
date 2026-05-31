"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum


class TranslationProvider(str, Enum):
    """Supported translation providers."""
    GOOGLE = "google"
    BAIDU = "baidu"
    SUAPI = "suapi"
    DEEPL = "deepl"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class FileUploadResponse(BaseModel):
    """Response for file upload."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    page_count: int = Field(..., description="Number of pages in PDF")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(default="uploaded", description="Upload status")


class TranslationRequest(BaseModel):
    """Request to start translation."""
    file_id: str = Field(..., description="File ID from upload")
    provider: TranslationProvider = Field(default=TranslationProvider.GOOGLE)
    api_key: Optional[str] = Field(None, description="API key for translation service")
    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="zh", description="Target language code")


class TranslationStatus(str, Enum):
    """Translation task status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranslationResponse(BaseModel):
    """Response for translation request."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TranslationStatus = Field(default=TranslationStatus.PENDING)
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    result: Optional[Dict[str, Any]] = Field(None, description="Translation result")


class TextBlock(BaseModel):
    """Text block with position info."""
    text: str = Field(..., description="Text content")
    bbox: Tuple[float, float, float, float] = Field(..., description="Bounding box (x0, y0, x1, y1)")
    font_size: float = Field(default=12.0)
    font_name: str = Field(default="")
    is_bold: bool = Field(default=False)
    is_italic: bool = Field(default=False)
    block_type: str = Field(default="text", description="text, formula, or image")


class Formula(BaseModel):
    """Formula block."""
    content: str = Field(..., description="LaTeX content")
    position: Tuple[int, int] = Field(..., description="Position in text")


class ImageBlock(BaseModel):
    """Image block."""
    image_id: str = Field(..., description="Unique image identifier")
    bbox: Tuple[float, float, float, float] = Field(..., description="Bounding box")
    width: int = Field(..., description="Image width")
    height: int = Field(..., description="Image height")


class PageContent(BaseModel):
    """Content of a single page."""
    page_number: int = Field(..., description="Page number (1-indexed)")
    text_blocks: List[TextBlock] = Field(default_factory=list)
    images: List[ImageBlock] = Field(default_factory=list)
    formulas: List[Formula] = Field(default_factory=list)
    translated_blocks: List[TextBlock] = Field(default_factory=list)


class PDFContent(BaseModel):
    """Complete PDF content."""
    file_id: str = Field(..., description="File identifier")
    filename: str = Field(..., description="Original filename")
    page_count: int = Field(..., description="Total pages")
    pages: List[PageContent] = Field(default_factory=list)


class ExportRequest(BaseModel):
    """Request to export translated document."""
    task_id: str = Field(..., description="Translation task ID")
    format: str = Field(default="pdf", description="Export format: pdf or docx")


class ExportResponse(BaseModel):
    """Response for export request."""
    download_url: str = Field(..., description="URL to download the file")
    filename: str = Field(..., description="Exported filename")
    file_size: int = Field(..., description="File size in bytes")


class ErrorResponse(BaseModel):
    """Error response."""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
