import boto3
import logging
from typing import Dict, Optional
from pathlib import Path
import uuid
from config import Config

logger = logging.getLogger(__name__)

class S3Uploader:
    """Class for uploading PDF documents to S3 for Lambda processing"""
    
    def __init__(self):
        self.config = Config()
        self.s3_client = None
        self.bucket_name = self.config.S3_BUCKET_NAME
        self._initialize_s3()
    
    def _initialize_s3(self):
        """Initialize S3 client"""
        try:
            session = boto3.Session(
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION
            )
            
            self.s3_client = session.client('s3')
            logger.info("Successfully initialized S3 client")
            
        except Exception as e:
            logger.error(f"Error initializing S3: {str(e)}")
            raise
    
    def upload_pdf_file(self, pdf_path: str, custom_key: Optional[str] = None) -> Dict[str, str]:
        """
        Upload PDF file to S3
        
        Args:
            pdf_path: Path to the PDF file
            custom_key: Optional custom S3 key, otherwise generates UUID
            
        Returns:
            Dictionary with upload details
        """
        try:
            file_path = Path(pdf_path)
            
            if not file_path.exists():
                raise ValueError(f"PDF file not found: {pdf_path}")
            
            if not file_path.suffix.lower() == '.pdf':
                raise ValueError(f"File is not a PDF: {pdf_path}")
            
            # Generate S3 key
            if custom_key:
                s3_key = f"legal-documents/{custom_key}"
            else:
                unique_id = str(uuid.uuid4())
                s3_key = f"legal-documents/{unique_id}/{file_path.name}"
            
            # Upload file
            with open(pdf_path, 'rb') as file:
                self.s3_client.upload_fileobj(
                    file,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'application/pdf',
                        'Metadata': {
                            'original_name': file_path.name,
                            'upload_type': 'legal_document'
                        }
                    }
                )
            
            # Generate pre-signed URL for download
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=3600  # 1 hour
            )
            
            result = {
                'success': True,
                'bucket': self.bucket_name,
                's3_key': s3_key,
                'download_url': download_url,
                'file_size': file_path.stat().st_size,
                'original_name': file_path.name
            }
            
            logger.info(f"Successfully uploaded {pdf_path} to s3://{self.bucket_name}/{s3_key}")
            return result
            
        except Exception as e:
            logger.error(f"Error uploading PDF to S3: {str(e)}")
            raise
    
    def upload_pdf_bytes(self, pdf_bytes: bytes, filename: str, custom_key: Optional[str] = None) -> Dict[str, str]:
        """
        Upload PDF bytes to S3
        
        Args:
            pdf_bytes: PDF content as bytes
            filename: Original filename
            custom_key: Optional custom S3 key
            
        Returns:
            Dictionary with upload details
        """
        try:
            # Generate S3 key
            if custom_key:
                s3_key = f"legal-documents/{custom_key}"
            else:
                unique_id = str(uuid.uuid4())
                s3_key = f"legal-documents/{unique_id}/{filename}"
            
            # Upload bytes
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType='application/pdf',
                Metadata={
                    'original_name': filename,
                    'upload_type': 'legal_document'
                }
            )
            
            # Generate pre-signed URL for download
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=3600
            )
            
            result = {
                'success': True,
                'bucket': self.bucket_name,
                's3_key': s3_key,
                'download_url': download_url,
                'file_size': len(pdf_bytes),
                'original_name': filename
            }
            
            logger.info(f"Successfully uploaded {filename} bytes to s3://{self.bucket_name}/{s3_key}")
            return result
            
        except Exception as e:
            logger.error(f"Error uploading PDF bytes to S3: {str(e)}")
            raise
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Successfully deleted s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting S3 object: {str(e)}")
            return False
    
    def check_file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            logger.error(f"Error checking S3 object existence: {str(e)}")
            return False
