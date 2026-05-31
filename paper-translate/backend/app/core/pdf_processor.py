"""PDF processing core module."""
import fitz  # PyMuPDF
import re
import os
import uuid
from typing import List, Tuple, Optional
from pathlib import Path

from app.models.schemas import (
    PageContent, TextBlock, Formula, ImageBlock, PDFContent
)


class PDFProcessor:
    """PDF processing core class."""
    
    # LaTeX formula patterns
    FORMULA_PATTERNS = [
        r'\$\$[^$]+\$\$',           # $$...$$ display math
        r'\$[^$]+\$',               # $...$ inline math
        r'\\\[[^\]]+\\\]',         # \[...\] display math
        r'\\\([^)]+\\\)',          # \(...\) inline math
        r'\\begin\{equation\}.*?\\end\{equation\}',  # equation environment
        r'\\begin\{align\}.*?\\end\{align\}',        # align environment
        r'\\begin\{eqnarray\}.*?\\end\{eqnarray\}',  # eqnarray environment
    ]
    
    def __init__(self, file_path: str):
        """Initialize PDF processor.
        
        Args:
            file_path: Path to PDF file
        """
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        # Derive file_id from the actual filename (uploads/{file_id}.pdf)
        # so that the serve endpoint can find the original file.
        stem = Path(file_path).stem
        if stem and len(stem) >= 32:
            self.file_id = stem
        else:
            self.file_id = str(uuid.uuid4())
    
    def get_info(self) -> dict:
        """Get PDF basic information."""
        return {
            "file_id": self.file_id,
            "page_count": len(self.doc),
            "metadata": dict(self.doc.metadata),
        }
    
    def extract_content(self) -> PDFContent:
        """Extract all content from PDF.
        
        Returns:
            PDFContent object containing all pages
        """
        pages = []
        for page_num in range(len(self.doc)):
            page_content = self._extract_page_content(page_num)
            pages.append(page_content)
        
        return PDFContent(
            file_id=self.file_id,
            filename=os.path.basename(self.file_path),
            page_count=len(self.doc),
            pages=pages
        )
    
    def _extract_page_content(self, page_num: int) -> PageContent:
        """Extract content from a single page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            PageContent object
        """
        page = self.doc[page_num]
        
        # Extract text blocks
        text_blocks = self._extract_text_blocks(page)
        
        # Extract images
        images = self._extract_images(page, page_num)
        
        # Detect formulas from text blocks
        formulas = self._detect_formulas(text_blocks)
        
        return PageContent(
            page_number=page_num + 1,  # 1-indexed
            text_blocks=text_blocks,
            images=images,
            formulas=formulas
        )
    
    def _extract_text_blocks(self, page: fitz.Page) -> List[TextBlock]:
        """Extract text blocks from page.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            List of TextBlock objects
        """
        blocks = []
        
        # Get text blocks with their bounding boxes
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            font = span.get("font", "")
                            flags = span.get("flags", 0)
                            
                            # Check if it's a formula by looking for math symbols
                            is_formula = self._is_formula_text(text)
                            
                            blocks.append(TextBlock(
                                text=text,
                                bbox=bbox,
                                font_size=span.get("size", 12.0),
                                font_name=font,
                                is_bold=bool(flags & 2**4),  # Check bold flag
                                is_italic=bool(flags & 2**1),  # Check italic flag
                                block_type="formula" if is_formula else "text"
                            ))
        
        # Sort blocks by vertical position (top to bottom)
        blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        
        return blocks
    
    def _is_formula_text(self, text: str) -> bool:
        """Check if text contains formula indicators.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be a formula
        """
        # Check for LaTeX delimiters
        if any(delim in text for delim in ['$', '\\(', '\\[', '\\begin{']):
            return True
        
        # Check for common math symbols
        math_symbols = set('∑∏∫√∞∂∆παβγδεθλμσφωΩ±×÷≤≥≠≈←↑→↓↔⇒⇔∈∉⊂⊃⊆⊇∪∩∧∨¬∀∃∴∵')
        if any(c in math_symbols for c in text):
            return True
        
        # Check for subscripts/superscripts patterns
        if re.search(r'[_^]\{?\w+\}?', text):
            return True
        
        return False
    
    def _extract_images(self, page: fitz.Page, page_num: int) -> List[ImageBlock]:
        """Extract images from page.
        
        Args:
            page: PyMuPDF page object
            page_num: Page number
            
        Returns:
            List of ImageBlock objects
        """
        images = []
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = self.doc.extract_image(xref)
            
            if base_image:
                image_id = f"page{page_num}_img{img_index}"
                
                # Get image position (approximate from page)
                # In a full implementation, we'd need to map xref to position
                images.append(ImageBlock(
                    image_id=image_id,
                    bbox=(0, 0, 100, 100),  # Placeholder
                    width=base_image.get("width", 0),
                    height=base_image.get("height", 0)
                ))
        
        return images
    
    def _detect_formulas(self, text_blocks: List[TextBlock]) -> List[Formula]:
        """Detect formulas in text blocks.
        
        Args:
            text_blocks: List of text blocks
            
        Returns:
            List of Formula objects
        """
        formulas = []
        
        for block in text_blocks:
            if block.block_type == "formula":
                # Try to extract LaTeX content
                text = block.text
                
                # Check for inline/display math delimiters
                for pattern in self.FORMULA_PATTERNS:
                    matches = re.finditer(pattern, text, re.DOTALL)
                    for match in matches:
                        formulas.append(Formula(
                            content=match.group(),
                            position=(match.start(), match.end())
                        ))
        
        return formulas
    
    def protect_formulas(self, text: str) -> Tuple[str, List[str]]:
        """Replace formulas with placeholders to protect them during translation.
        
        Args:
            text: Original text
            
        Returns:
            Tuple of (protected_text, list_of_formulas)
        """
        formulas = []
        protected_text = text
        
        # Find all formulas and replace with placeholders
        for pattern in self.FORMULA_PATTERNS:
            matches = list(re.finditer(pattern, protected_text, re.DOTALL))
            # Replace in reverse order to maintain positions
            for match in reversed(matches):
                formula = match.group()
                formulas.insert(0, formula)
                placeholder = f"[[FORMULA_{len(formulas)-1}]]"
                protected_text = protected_text[:match.start()] + placeholder + protected_text[match.end():]
        
        return protected_text, formulas
    
    def restore_formulas(self, text: str, formulas: List[str]) -> str:
        """Restore formulas from placeholders.
        
        Args:
            text: Text with placeholders
            formulas: List of original formulas
            
        Returns:
            Text with formulas restored
        """
        result = text
        for i, formula in enumerate(formulas):
            placeholder = f"[[FORMULA_{i}]]"
            result = result.replace(placeholder, formula)
        return result
    
    def close(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
