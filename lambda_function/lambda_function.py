import json
import boto3
import PyPDF2
import io
import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

@dataclass
class Clause:
    """Data class representing a legal clause"""
    clause_name: str
    content: str
    clause_type: Optional[str] = None
    section_number: Optional[str] = None
    page_reference: Optional[str] = None

def lambda_handler(event, context):
    """
    AWS Lambda function to process legal documents and extract clauses using regex
    
    Expected event format:
    {
        "bucket": "bucket-name",
        "key": "path/to/document.pdf",
        "clause_types": ["Terms and Conditions", "Payment Terms", ...]
    }
    """
    try:
        # Extract parameters from event
        bucket = event['bucket']
        key = event['key']
        clause_types = event.get('clause_types', [])
        
        logger.info(f"Processing document: s3://{bucket}/{key}")
        
        # Download PDF from S3 and extract text
        pdf_text = extract_text_from_s3_pdf(bucket, key)
        
        # Initialize clause extractor
        extractor = ClauseExtractor()
        
        # Extract clauses using deterministic regex approach
        extracted_clauses = extractor.extract_clauses_by_type(pdf_text, clause_types)
        
        # Get detailed clause information
        detailed_clauses = extractor.split_into_clauses(pdf_text)
        grouped_detailed = extractor.group_clauses_by_type(detailed_clauses)
        
        # Prepare response with both simplified and detailed formats
        response = {
            'statusCode': 200,
            'body': {
                'success': True,
                'document_info': {
                    'bucket': bucket,
                    'key': key,
                    'text_length': len(pdf_text),
                    'total_clauses_found': len(detailed_clauses)
                },
                'extracted_clauses': extracted_clauses,
                'detailed_clauses': {
                    clause_type: [asdict(clause) for clause in clauses]
                    for clause_type, clauses in grouped_detailed.items()
                },
                'processing_metadata': {
                    'extraction_method': 'regex_deterministic',
                    'total_clauses_found': len(detailed_clauses),
                    'clause_types_found': list(grouped_detailed.keys()),
                    'clause_types_requested': clause_types
                }
            }
        }
        
        logger.info(f"Document processing completed successfully. Found {len(detailed_clauses)} clauses")
        return response
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
        }

def extract_text_from_s3_pdf(bucket: str, key: str) -> str:
    """
    Extract text from PDF stored in S3
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        Extracted text from PDF
    """
    try:
        # Download PDF from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_content = response['Body'].read()
        
        # Extract text using PyPDF2
        pdf_stream = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        
        text = ""
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
        logger.error(f"Error extracting text from S3 PDF: {str(e)}")
        raise

class ClauseExtractor:
    """Deterministic clause extractor using regex patterns for legal documents"""
    
    def __init__(self):
        # Enhanced patterns for legal document clause identification
        self.clause_patterns = [
            # Section/Article/Clause with numbers (e.g., "Section 1.1", "Article 5", "Clause 3.2.1")
            r"(?P<title>(?:Section|Article|Clause|Schedule|Paragraph|Part|Chapter)\s+\d+(?:\.\d+)*(?:\.\d+)*[^\n]*)",
            
            # Numbered headings (e.g., "1.", "2.1", "3.2.1")
            r"(?P<title>\d+(?:\.\d+)*(?:\.\d+)*\.?\s+[A-Z][^\n]*)",
            
            # Lettered sections (e.g., "(a)", "(i)", "A.")
            r"(?P<title>\([a-z]+\)|[A-Z]\.)\s+[^\n]*",
            
            # Common legal headings without numbers
            r"(?P<title>(?:WHEREAS|NOW THEREFORE|DEFINITIONS|TERMS AND CONDITIONS|PAYMENT|TERMINATION|LIABILITY|CONFIDENTIALITY|INTELLECTUAL PROPERTY|GOVERNING LAW|DISPUTE RESOLUTION|FORCE MAJEURE|AMENDMENTS|WARRANTIES|REPRESENTATIONS)[^\n]*)"
        ]
        
        # Clause type classification patterns
        self.clause_type_patterns = {
            "Terms and Conditions": [
                r"terms?\s+and\s+conditions?",
                r"general\s+terms?",
                r"conditions?\s+of\s+use",
                r"agreement\s+terms?"
            ],
            "Payment Terms": [
                r"payment\s+terms?",
                r"payment\s+obligations?",
                r"fees?\s+and\s+charges?",
                r"billing",
                r"invoice",
                r"compensation"
            ],
            "Termination Clause": [
                r"termination",
                r"expir(?:ation|y)",
                r"end\s+of\s+agreement",
                r"dissolution"
            ],
            "Liability Clause": [
                r"liability",
                r"damages?",
                r"limitation\s+of\s+liability",
                r"indemnif(?:ication|y)",
                r"harm",
                r"loss"
            ],
            "Confidentiality Clause": [
                r"confidential(?:ity)?",
                r"non\-?disclosure",
                r"proprietary\s+information",
                r"trade\s+secrets?",
                r"privacy"
            ],
            "Intellectual Property": [
                r"intellectual\s+property",
                r"copyright",
                r"trademark",
                r"patent",
                r"proprietary\s+rights?",
                r"ownership"
            ],
            "Governing Law": [
                r"governing\s+law",
                r"applicable\s+law",
                r"jurisdiction",
                r"venue",
                r"choice\s+of\s+law"
            ],
            "Dispute Resolution": [
                r"dispute\s+resolution",
                r"arbitration",
                r"mediation",
                r"litigation",
                r"legal\s+proceedings?"
            ],
            "Force Majeure": [
                r"force\s+majeure",
                r"act\s+of\s+god",
                r"unforeseeable\s+circumstances?",
                r"beyond\s+(?:reasonable\s+)?control"
            ],
            "Amendments": [
                r"amendment",
                r"modification",
                r"changes?\s+to\s+agreement",
                r"variation"
            ],
            "Definitions": [
                r"definitions?",
                r"interpretation",
                r"meaning",
                r"shall\s+mean"
            ],
            "Representations and Warranties": [
                r"representations?\s+and\s+warrant(?:ies|y)",
                r"representations?",
                r"warrant(?:ies|y)",
                r"guarantees?",
                r"assurances?"
            ]
        }
    
    def split_into_clauses(self, text: str) -> List[Clause]:
        """Split legal document text into individual clauses using regex patterns"""
        try:
            all_matches = []
            
            # Find all clause headings using different patterns
            for pattern in self.clause_patterns:
                matches = list(re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE))
                all_matches.extend(matches)
            
            # Sort matches by position in text
            all_matches.sort(key=lambda x: x.start())
            
            # Remove duplicate matches (overlapping patterns)
            unique_matches = self._remove_duplicate_matches(all_matches)
            
            clauses = []
            for i, match in enumerate(unique_matches):
                start = match.start()
                end = unique_matches[i + 1].start() if i + 1 < len(unique_matches) else len(text)
                
                title = match.group("title").strip() if "title" in match.groupdict() else match.group(0).strip()
                content = text[start:end].strip()
                
                # Extract section number if present
                section_number = self._extract_section_number(title)
                
                # Classify clause type
                clause_type = self._classify_clause_type(title, content)
                
                # Extract page reference if present
                page_reference = self._extract_page_reference(content)
                
                clause = Clause(
                    clause_name=title,
                    content=content,
                    clause_type=clause_type,
                    section_number=section_number,
                    page_reference=page_reference
                )
                
                clauses.append(clause)
            
            logger.info(f"Successfully extracted {len(clauses)} clauses from document")
            return clauses
            
        except Exception as e:
            logger.error(f"Error splitting document into clauses: {str(e)}")
            raise
    
    def _remove_duplicate_matches(self, matches: List) -> List:
        """Remove overlapping or duplicate matches"""
        if not matches:
            return matches
        
        unique_matches = [matches[0]]
        
        for match in matches[1:]:
            # Check if this match overlaps significantly with the last unique match
            last_match = unique_matches[-1]
            
            if match.start() >= last_match.end() - 10:  # Allow small overlap
                unique_matches.append(match)
        
        return unique_matches
    
    def _extract_section_number(self, title: str) -> Optional[str]:
        """Extract section number from clause title"""
        try:
            number_pattern = r"(\d+(?:\.\d+)*(?:\.\d+)*)"
            match = re.search(number_pattern, title)
            return match.group(1) if match else None
        except Exception:
            return None
    
    def _classify_clause_type(self, title: str, content: str) -> Optional[str]:
        """Classify clause type based on title and content"""
        try:
            text_to_analyze = (title + " " + content[:500]).lower()
            
            for clause_type, patterns in self.clause_type_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_to_analyze, re.IGNORECASE):
                        return clause_type
            
            return None
        except Exception:
            return None
    
    def _extract_page_reference(self, content: str) -> Optional[str]:
        """Extract page reference from clause content"""
        try:
            page_pattern = r"---\s*Page\s+(\d+)\s*---"
            match = re.search(page_pattern, content)
            return match.group(1) if match else None
        except Exception:
            return None
    
    def group_clauses_by_type(self, clauses: List[Clause]) -> Dict[str, List[Clause]]:
        """Group clauses by their classified type"""
        grouped_clauses = {}
        
        for clause in clauses:
            clause_type = clause.clause_type or "Unclassified"
            
            if clause_type not in grouped_clauses:
                grouped_clauses[clause_type] = []
            
            grouped_clauses[clause_type].append(clause)
        
        return grouped_clauses
    
    def extract_clauses_by_type(self, text: str, target_clause_types: List[str] = None) -> Dict[str, List[str]]:
        """Extract and group clauses by type, returning simplified format"""
        try:
            # Split document into clauses
            clauses = self.split_into_clauses(text)
            
            # Group by type
            grouped_clauses = self.group_clauses_by_type(clauses)
            
            # Convert to simplified format
            result = {}
            
            target_types = target_clause_types or list(self.clause_type_patterns.keys())
            
            for clause_type in target_types:
                if clause_type in grouped_clauses:
                    result[clause_type] = [clause.content for clause in grouped_clauses[clause_type]]
                else:
                    result[clause_type] = []
            
            # Also include unclassified clauses if no specific types requested
            if not target_clause_types and "Unclassified" in grouped_clauses:
                result["Unclassified"] = [clause.content for clause in grouped_clauses["Unclassified"]]
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting clauses by type: {str(e)}")
            raise
