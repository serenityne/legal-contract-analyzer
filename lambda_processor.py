import boto3
import json
import logging
from typing import Dict, List, Optional
from config import Config

logger = logging.getLogger(__name__)

class LambdaProcessor:
    """Class for invoking AWS Lambda function to process legal documents"""
    
    def __init__(self):
        self.config = Config()
        self.lambda_client = None
        self._initialize_lambda()
    
    def _initialize_lambda(self):
        """Initialize Lambda client"""
        try:
            session = boto3.Session(
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION
            )
            
            self.lambda_client = session.client('lambda')
            logger.info("Successfully initialized Lambda client")
            
        except Exception as e:
            logger.error(f"Error initializing Lambda: {str(e)}")
            raise
    
    def invoke_document_processor(self, s3_bucket: str, s3_key: str) -> Dict:
        """
        Invoke Lambda function to process legal document
        
        Args:
            s3_bucket: S3 bucket name where document is stored
            s3_key: S3 key of the document
            
        Returns:
            Dictionary with processing results
        """
        try:
            payload = {
                'bucket': s3_bucket,
                'key': s3_key,
                'clause_types': self.config.CLAUSE_TYPES
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.config.LAMBDA_FUNCTION_NAME,
                InvocationType='RequestResponse',  # Synchronous invocation
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                if 'errorMessage' in response_payload:
                    raise Exception(f"Lambda execution error: {response_payload['errorMessage']}")
                
                logger.info("Successfully processed document via Lambda")
                return response_payload
            else:
                raise Exception(f"Lambda invocation failed with status code: {response['StatusCode']}")
                
        except Exception as e:
            logger.error(f"Error invoking Lambda function: {str(e)}")
            raise
    
    def invoke_document_processor_async(self, s3_bucket: str, s3_key: str, callback_url: Optional[str] = None) -> str:
        """
        Invoke Lambda function asynchronously to process legal document
        
        Args:
            s3_bucket: S3 bucket name where document is stored
            s3_key: S3 key of the document
            callback_url: Optional URL to call when processing is complete
            
        Returns:
            Request ID for tracking
        """
        try:
            payload = {
                'bucket': s3_bucket,
                'key': s3_key,
                'clause_types': self.config.CLAUSE_TYPES,
                'callback_url': callback_url
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.config.LAMBDA_FUNCTION_NAME,
                InvocationType='Event',  # Asynchronous invocation
                Payload=json.dumps(payload)
            )
            
            if response['StatusCode'] == 202:  # Accepted for async processing
                request_id = response['ResponseMetadata']['RequestId']
                logger.info(f"Successfully queued document for processing. Request ID: {request_id}")
                return request_id
            else:
                raise Exception(f"Lambda async invocation failed with status code: {response['StatusCode']}")
                
        except Exception as e:
            logger.error(f"Error invoking Lambda function asynchronously: {str(e)}")
            raise
    
    def get_processing_status(self, request_id: str) -> Dict:
        """
        Get processing status for a document (requires additional DynamoDB setup)
        
        Args:
            request_id: Request ID from async invocation
            
        Returns:
            Dictionary with status information
        """
        try:
            # This would typically query DynamoDB for status
            # For now, we'll return a placeholder
            return {
                'request_id': request_id,
                'status': 'processing',
                'message': 'Status tracking requires DynamoDB setup'
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {str(e)}")
            raise
