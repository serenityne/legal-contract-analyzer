import PyPDF2
import logging
from typing import List, Dict, Optional
from pathlib import Path
import io

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Class for processing PDF documents and extracting text"""
    
    def __init__(self, max_size_mb: int = 50):
        self.max_size_mb = max_size_mb
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text as string
        """
        try:
            # Check file size
            file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_size_mb:
                raise ValueError(f"PDF file size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({self.max_size_mb} MB)")
            
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from each page
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n--- Page {page_num + 1} ---\n"
                            text += page_text
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                        continue
            
            if not text.strip():
                raise ValueError("No text could be extracted from the PDF")
                
            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
    
    def extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            Extracted text as string
        """
        try:
            # Check size
            size_mb = len(pdf_bytes) / (1024 * 1024)
            if size_mb > self.max_size_mb:
                raise ValueError(f"PDF size ({size_mb:.2f} MB) exceeds maximum allowed size ({self.max_size_mb} MB)")
            
            text = ""
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                    continue
            
            if not text.strip():
                raise ValueError("No text could be extracted from the PDF")
                
            logger.info(f"Successfully extracted {len(text)} characters from PDF bytes")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error processing PDF bytes: {str(e)}")
            raise
    
    def validate_pdf(self, pdf_path: str) -> Dict[str, any]:
        """
        Validate PDF file and return metadata
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing validation results and metadata
        """
        try:
            file_path = Path(pdf_path)
            
            if not file_path.exists():
                return {"valid": False, "error": "File does not exist"}
            
            if not file_path.suffix.lower() == '.pdf':
                return {"valid": False, "error": "File is not a PDF"}
            
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            with open(pdf_path, 'rb') as file:
                try:
                    pdf_reader = PyPDF2.PdfReader(file)
                    num_pages = len(pdf_reader.pages)
                    
                    metadata = {
                        "valid": True,
                        "file_size_mb": round(file_size_mb, 2),
                        "num_pages": num_pages,
                        "file_path": str(file_path),
                        "metadata": pdf_reader.metadata if pdf_reader.metadata else {}
                    }
                    
                    return metadata
                    
                except Exception as e:
                    return {"valid": False, "error": f"Invalid PDF format: {str(e)}"}
                    
        except Exception as e:
            return {"valid": False, "error": f"Error validating PDF: {str(e)}"}
