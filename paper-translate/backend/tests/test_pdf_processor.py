import pytest
import tempfile
import os
from app.core.pdf_processor import PDFProcessor
from app.models.schemas import PDFContent, PageContent, TextBlock, Formula, ImageBlock

class TestPDFProcessor:
    @pytest.fixture
    def test_pdf_path(self):
        # Create a simple test PDF file
        # For actual testing, you would use a real PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>endobj\n4 0 obj<< /Length 30 >>stream\nBT /F1 12 Tf 100 700 Td (Hello World) Tj ET\nendstream\nendobj\n5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\nxref
0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000101 00000 n \n0000000185 00000 n \n0000000270 00000 n \ntrailer<< /Size 6 /Root 1 0 R >>\n%%EOF')
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    def test_init(self, test_pdf_path):
        """Test PDFProcessor initialization"""
        processor = PDFProcessor(test_pdf_path)
        assert processor.file_path == test_pdf_path
        assert processor.doc is not None
        assert processor.file_id is not None
        processor.close()

    def test_get_info(self, test_pdf_path):
        """Test get_info method"""
        with PDFProcessor(test_pdf_path) as processor:
            info = processor.get_info()
            assert "file_id" in info
            assert "page_count" in info
            assert "metadata" in info
            assert info["page_count"] == 1

    def test_extract_content(self, test_pdf_path):
        """Test extract_content method"""
        with PDFProcessor(test_pdf_path) as processor:
            content = processor.extract_content()
            assert isinstance(content, PDFContent)
            assert content.file_id == processor.file_id
            assert content.page_count == 1
            assert len(content.pages) == 1

    def test_protect_formulas(self):
        """Test formula protection"""
        test_text = "This is a formula: $E=mc^2$ and another: \(x^2 + y^2 = z^2\)"
        processor = PDFProcessor("dummy.pdf")  # Dummy path for testing
        protected_text, formulas = processor.protect_formulas(test_text)
        assert "[[FORMULA_0]]" in protected_text
        assert "[[FORMULA_1]]" in protected_text
        assert len(formulas) == 2
        assert "$E=mc^2$" in formulas
        assert "\(x^2 + y^2 = z^2\)" in formulas

    def test_restore_formulas(self):
        """Test formula restoration"""
        test_text = "This is a formula: [[FORMULA_0]] and another: [[FORMULA_1]]"
        formulas = ["$E=mc^2$", "\(x^2 + y^2 = z^2\)"]
        processor = PDFProcessor("dummy.pdf")  # Dummy path for testing
        restored_text = processor.restore_formulas(test_text, formulas)
        assert "$E=mc^2$" in restored_text
        assert "\(x^2 + y^2 = z^2\)" in restored_text