import os
from dotenv import load_dotenv
from typing import Optional
import logging

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the legal document analyzer"""
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    BEDROCK_EMBEDDING_MODEL_ID: str = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1")
    
    # S3 Configuration
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "legal-document-analyzer-bucket")
    
    # Lambda Configuration
    LAMBDA_FUNCTION_NAME: str = os.getenv("LAMBDA_FUNCTION_NAME", "legal-document-processor")
    
    # Application Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_PDF_SIZE_MB: int = int(os.getenv("MAX_PDF_SIZE_MB", "50"))
    
    # Clause Extraction Configuration
    CLAUSE_TYPES = [
        "Terms and Conditions",
        "Payment Terms",
        "Termination Clause",
        "Liability Clause", 
        "Confidentiality Clause",
        "Intellectual Property",
        "Governing Law",
        "Dispute Resolution",
        "Force Majeure",
        "Amendments",
        "Definitions",
        "Representations and Warranties"
    ]

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
