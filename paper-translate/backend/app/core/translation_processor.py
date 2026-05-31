"""Translation processor for PDF documents.

Core strategy (inspired by 小绿鲸 academic translation approach):
1. Extract text at paragraph level (not individual spans)
2. Protect formulas, citations, references before translation
3. Translate paragraphs as complete units for context preservation
4. Map translated paragraphs back to original text blocks
"""

import asyncio
import re
from typing import Optional, Callable, List, Tuple
from pathlib import Path

from app.models.schemas import (
    PDFContent, PageContent, TextBlock, TranslationProvider, TranslationStatus
)
from app.core.pdf_processor import PDFProcessor
from app.services.translation_service import TranslationEngine
import logging

logger = logging.getLogger(__name__)


class TranslationProcessor:
    """Process PDF translation tasks with paragraph-level translation."""

    def __init__(
        self,
        file_path: str,
        provider: TranslationProvider,
        api_key: Optional[str] = None,
        source_lang: str = "en",
        target_lang: str = "zh"
    ):
        self.file_path = file_path
        self.provider = provider
        self.api_key = api_key
        self.source_lang = source_lang
        self.target_lang = target_lang

        self.pdf_processor = PDFProcessor(file_path)
        self.translation_engine = TranslationEngine(provider, api_key)

        self.status = TranslationStatus.PENDING
        self.progress = 0.0
        self.message = ""
        self.result: Optional[PDFContent] = None
        self._cancelled = False

    async def process(
        self,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> PDFContent:
        """Process the translation."""
        self.status = TranslationStatus.PROCESSING
        self.message = "正在解析PDF..."

        try:
            # Step 1: Extract PDF content
            pdf_content = self.pdf_processor.extract_content()
            total_pages = len(pdf_content.pages)

            if self._cancelled:
                raise asyncio.CancelledError()

            # Step 2: Merge text blocks into paragraphs per page, then translate
            for i, page in enumerate(pdf_content.pages):
                if self._cancelled:
                    raise asyncio.CancelledError()

                self.message = f"正在翻译第 {i+1}/{total_pages} 页..."
                await self._translate_page_paragraph(page)

                # Update progress
                self.progress = ((i + 1) / total_pages) * 100
                if progress_callback:
                    progress_callback(self.progress, self.message)

            self.status = TranslationStatus.COMPLETED
            self.progress = 100.0
            self.message = "翻译完成"
            self.result = pdf_content

            return pdf_content

        except asyncio.CancelledError:
            self.status = TranslationStatus.FAILED
            self.message = "翻译已取消"
            raise
        except Exception as e:
            self.status = TranslationStatus.FAILED
            self.message = f"翻译失败: {str(e)}"
            raise

    def _merge_blocks_to_paragraphs(
        self, blocks: List[TextBlock], y_threshold: float = 3.0
    ) -> List[Tuple[List[int], str]]:
        """Merge text blocks into paragraphs based on vertical proximity.

        Blocks that are close vertically (within y_threshold points) are
        grouped into the same paragraph. Formula blocks break paragraphs.

        Args:
            blocks: List of text blocks from a page
            y_threshold: Max vertical gap (in points) to merge blocks

        Returns:
            List of (block_indices, merged_text) tuples
        """
        if not blocks:
            return []

        paragraphs = []
        current_indices = []
        current_text_parts = []

        for i, block in enumerate(blocks):
            # Skip formula blocks - they'll be preserved as-is
            if block.block_type == "formula":
                # Flush current paragraph before formula
                if current_indices:
                    text = " ".join(current_text_parts)
                    paragraphs.append((list(current_indices), text))
                    current_indices = []
                    current_text_parts = []
                # Keep formula as its own "paragraph" (won't be translated)
                continue

            if not block.text.strip():
                continue

            # Check vertical gap to previous block
            if current_indices:
                prev_idx = current_indices[-1]
                prev_bottom = blocks[prev_idx].bbox[3]
                curr_top = block.bbox[1]
                gap = curr_top - prev_bottom

                # Large gap = new paragraph (heuristic: line height * 1.5)
                prev_height = blocks[prev_idx].bbox[3] - blocks[prev_idx].bbox[1]
                line_spacing = prev_height * 1.8 if prev_height > 0 else 20

                if gap > line_spacing or gap > y_threshold * 5:
                    # New paragraph
                    text = " ".join(current_text_parts)
                    paragraphs.append((list(current_indices), text))
                    current_indices = []
                    current_text_parts = []

            current_indices.append(i)
            current_text_parts.append(block.text)

        # Flush last paragraph
        if current_indices:
            text = " ".join(current_text_parts)
            paragraphs.append((list(current_indices), text))

        return paragraphs

    async def _translate_page_paragraph(self, page: PageContent):
        """Translate a page by merging blocks into paragraphs for better context.

        This is the key improvement over span-level translation:
        - Merge nearby text spans into paragraphs
        - Translate complete paragraphs for better context
        - Split translated paragraphs back to individual blocks
        """
        # Separate text blocks (translate) from formula blocks (preserve)
        text_blocks = page.text_blocks

        if not text_blocks:
            return

        # Build a mapping from text blocks that need translation
        # Block indices that are formulas -> add to translated_blocks as-is
        for block in text_blocks:
            if block.block_type == "formula":
                page.translated_blocks.append(TextBlock(
                    text=block.text,
                    bbox=block.bbox,
                    font_size=block.font_size,
                    font_name=block.font_name,
                    is_bold=block.is_bold,
                    is_italic=block.is_italic,
                    block_type="formula"
                ))

        # Get only text-type blocks for paragraph merging
        text_only_indices = [i for i, b in enumerate(text_blocks) if b.block_type == "text"]
        if not text_only_indices:
            return

        text_only_blocks = [text_blocks[i] for i in text_only_indices]

        # Merge into paragraphs
        paragraphs = self._merge_blocks_to_paragraphs(text_only_blocks)

        if not paragraphs:
            return

        # Translate paragraphs in batches
        batch_size = 5  # Fewer parallel requests to respect rate limits
        translated_paragraphs = []

        for batch_start in range(0, len(paragraphs), batch_size):
            if self._cancelled:
                raise asyncio.CancelledError()

            batch = paragraphs[batch_start:batch_start + batch_size]
            batch_texts = [text for _, text in batch]

            # Add delay between batches
            if batch_start > 0:
                await asyncio.sleep(1.0)

            batch_results = await self.translation_engine.translate_batch(
                batch_texts,
                self.source_lang,
                self.target_lang
            )
            translated_paragraphs.extend(batch_results)

        # Store translated paragraphs as whole blocks (one per paragraph)
        # instead of splitting back to individual spans — this keeps
        # the translation readable instead of fragmented.
        para_idx = 0

        for para_indices, _ in paragraphs:
            if para_idx >= len(translated_paragraphs):
                break

            translated_para = translated_paragraphs[para_idx]
            # Use the first block's position/font as the paragraph anchor
            first_block = text_blocks[para_indices[0]]

            page.translated_blocks.append(TextBlock(
                text=translated_para,
                bbox=first_block.bbox,
                font_size=first_block.font_size,
                font_name=first_block.font_name,
                is_bold=first_block.is_bold,
                is_italic=first_block.is_italic,
                block_type="text"
            ))

            para_idx += 1

    def _distribute_translation(
        self,
        translated: str,
        original_blocks: List[TextBlock]
    ) -> List[str]:
        """Distribute translated paragraph text back to original blocks.

        Uses sentence-level splitting to maintain readability.
        """
        if len(original_blocks) == 1:
            return [translated]

        # Split translated text into sentences
        sentences = re.split(r'(?<=[。！？.!?\]])', translated)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            # Fallback: just assign based on character ratio
            return self._distribute_by_ratio(translated, original_blocks)

        # Calculate total original length for ratio distribution
        total_len = sum(len(b.text) for b in original_blocks)

        result = []
        sent_idx = 0
        current_text = ""

        for i, block in enumerate(original_blocks):
            # Target length for this block
            target_ratio = len(block.text) / total_len if total_len > 0 else 1 / len(original_blocks)
            is_last = (i == len(original_blocks) - 1)

            # Accumulate sentences until we reach roughly the target proportion
            target_len = len(translated) * target_ratio

            while sent_idx < len(sentences):
                if not current_text:
                    current_text = sentences[sent_idx]
                    sent_idx += 1
                elif len(current_text) < target_len or is_last:
                    current_text += sentences[sent_idx]
                    sent_idx += 1
                else:
                    break

            if is_last:
                # Assign all remaining text to last block
                remaining = "".join(sentences[sent_idx:])
                if remaining:
                    current_text += remaining
                sent_idx = len(sentences)

            result.append(current_text.strip())
            current_text = ""

        # Fill any empty results
        while len(result) < len(original_blocks):
            result.append("")

        return result

    def _distribute_by_ratio(
        self,
        translated: str,
        blocks: List[TextBlock]
    ) -> List[str]:
        """Simple character-ratio distribution fallback."""
        total_len = sum(len(b.text) for b in blocks)
        if total_len == 0:
            return [translated] + [""] * (len(blocks) - 1)

        result = []
        pos = 0
        for block in blocks:
            ratio = len(block.text) / total_len
            length = int(len(translated) * ratio)
            result.append(translated[pos:pos + length].strip())
            pos += length

        # Ensure all text is distributed
        if result:
            result[-1] = translated[pos:].strip()

        return result

    def cancel(self):
        """Cancel the translation process."""
        self._cancelled = True

    def get_status(self) -> dict:
        """Get current translation status."""
        return {
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
        }

    def close(self):
        """Clean up resources."""
        self.pdf_processor.close()
