# Legal Document Analyzer

A comprehensive legal document analysis tool that extracts and categorizes different types of clauses from PDF documents using deterministic regex patterns. The system supports both local processing and AWS Lambda cloud processing.

## 🚀 Features

- **PDF Document Processing**: Extract text from PDF legal documents
- **Deterministic Clause Extraction**: Use regex patterns to identify and extract different types of legal clauses
- **Dual Processing Methods**: 
  - Local processing using regex patterns
  - AWS Lambda cloud processing with S3 storage
- **Interactive Web Interface**: Streamlit-based UI for easy document upload and analysis
- **Comprehensive Clause Types**: Supports 12+ different clause types including:
  - Terms and Conditions
  - Payment Terms
  - Termination Clauses
  - Liability Clauses
  - Confidentiality Clauses
  - Intellectual Property
  - Governing Law
  - Dispute Resolution
  - Force Majeure
  - Amendments
  - Definitions
  - Representations and Warranties

## 📋 Requirements

- Python 3.8+
- AWS Account (for Lambda processing)
- Required Python packages (see `requirements.txt`)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd legal-contract-analyzer
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials and configuration
   ```

4. **Configure AWS (for Lambda processing)**:
   - Set up AWS credentials
   - Create an S3 bucket for document storage
   - Deploy the Lambda function (see deployment section)

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1

# S3 Configuration
S3_BUCKET_NAME=legal-document-analyzer-bucket

# Lambda Configuration
LAMBDA_FUNCTION_NAME=legal-document-processor

# Application Configuration
LOG_LEVEL=INFO
MAX_PDF_SIZE_MB=50
```

## 🚀 Usage

### Running the Application

1. **Start the Streamlit application**:
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** and navigate to `http://localhost:8501`

3. **Upload a PDF document** and select the clause types you want to extract

4. **Choose processing method**:
   - **Local Processing**: Fast, runs locally using regex patterns
   - **AWS Lambda Processing**: Scalable cloud processing with S3 storage

### Using Individual Components

#### PDF Processing
```python
from pdf_processor import PDFProcessor

processor = PDFProcessor()
text = processor.extract_text_from_pdf("document.pdf")
```

#### Clause Extraction
```python
from clause_extractor import ClauseExtractor

extractor = ClauseExtractor()
clauses = extractor.extract_clauses_by_type(text, ["Payment Terms", "Termination Clause"])
```

#### S3 Upload
```python
from s3_uploader import S3Uploader

uploader = S3Uploader()
result = uploader.upload_pdf_file("document.pdf")
```

#### Lambda Processing
```python
from lambda_processor import LambdaProcessor

processor = LambdaProcessor()
result = processor.invoke_document_processor(bucket, s3_key)
```

## 🏗️ Architecture

### Local Processing Flow
```
PDF Upload → Text Extraction → Regex Clause Detection → Classification → Results Display
```

### AWS Lambda Processing Flow
```
PDF Upload → S3 Storage → Lambda Trigger → Text Extraction → Clause Detection → Results Return
```

### Components

1. **PDF Processor** (`pdf_processor.py`): Handles PDF text extraction using PyPDF2
2. **Clause Extractor** (`clause_extractor.py`): Deterministic regex-based clause extraction and classification
3. **S3 Uploader** (`s3_uploader.py`): Manages PDF uploads to AWS S3
4. **Lambda Processor** (`lambda_processor.py`): Handles Lambda function invocation
5. **Streamlit App** (`app.py`): Web interface for document analysis
6. **Lambda Function** (`lambda_function/lambda_function.py`): AWS Lambda handler for cloud processing

## 🔧 AWS Lambda Deployment

### Prerequisites
- AWS CLI configured
- Appropriate IAM permissions for Lambda, S3, and CloudWatch

### Deployment Steps

1. **Create deployment package**:
   ```bash
   cd lambda_function
   pip install PyPDF2 -t .
   zip -r lambda_function.zip .
   ```

2. **Create Lambda function**:
   ```bash
   aws lambda create-function \
     --function-name legal-document-processor \
     --runtime python3.9 \
     --role arn:aws:iam::YOUR-ACCOUNT:role/lambda-execution-role \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://lambda_function.zip \
     --timeout 300 \
     --memory-size 1024
   ```

3. **Create S3 bucket**:
   ```bash
   aws s3 mb s3://legal-document-analyzer-bucket
   ```

4. **Set up IAM permissions**:
   - Lambda execution role with S3 read/write permissions
   - CloudWatch logs permissions

### IAM Policy Example
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::legal-document-analyzer-bucket/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
```

## 📊 Clause Detection Patterns

The system uses sophisticated regex patterns to identify various clause types:

### Section Patterns
- `Section 1.1`, `Article 5`, `Clause 3.2.1`
- Numbered headings: `1.`, `2.1`, `3.2.1`
- Lettered sections: `(a)`, `(i)`, `A.`
- Legal headings: `WHEREAS`, `DEFINITIONS`, etc.

### Classification Patterns
Each clause type has specific keyword patterns for accurate classification:
- **Payment Terms**: `payment terms`, `billing`, `invoice`, `compensation`
- **Termination**: `termination`, `expiration`, `end of agreement`
- **Liability**: `liability`, `damages`, `limitation of liability`, `indemnification`

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Test PDF processing
python test_pdf_processor.py

# Test clause extraction
python test_clause_extractor.py

# Test full integration (requires AWS setup)
python test_integration.py
```

## 📈 Performance

### Local Processing
- **Speed**: ~1-2 seconds per document
- **Memory**: Low memory footprint
- **Scalability**: Limited by local resources

### Lambda Processing
- **Speed**: ~5-10 seconds per document (including upload)
- **Memory**: Configurable (512MB - 3GB)
- **Scalability**: Auto-scaling, handles concurrent requests

## 🔍 Troubleshooting

### Common Issues

1. **PDF Text Extraction Fails**:
   - Ensure PDF is not password-protected
   - Check if PDF contains extractable text (not just images)

2. **AWS Lambda Timeout**:
   - Increase Lambda timeout (max 15 minutes)
   - Optimize PDF size or split large documents

3. **S3 Upload Fails**:
   - Check AWS credentials and permissions
   - Verify S3 bucket exists and is accessible

4. **No Clauses Found**:
   - Document may not follow standard legal formatting
   - Try adjusting regex patterns in `clause_extractor.py`

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Output Formats

### JSON Output
```json
{
  "success": true,
  "document_info": {
    "filename": "contract.pdf",
    "text_length": 15420,
    "total_clauses_found": 12
  },
  "extracted_clauses": {
    "Payment Terms": ["Payment shall be made within 30 days..."],
    "Termination Clause": ["This agreement may be terminated..."]
  },
  "detailed_clauses": {
    "Payment Terms": [
      {
        "clause_name": "Section 3. Payment Terms",
        "content": "Payment shall be made within 30 days...",
        "section_number": "3",
        "page_reference": "2"
      }
    ]
  }
}
```

### CSV Export
- Clause type, name, section number, page reference, and full content
- Suitable for spreadsheet analysis and reporting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋‍♂️ Support

For questions or issues:
1. Check the troubleshooting section
2. Review existing GitHub issues
3. Create a new issue with detailed information

## 🔮 Future Enhancements

- Support for additional document formats (DOCX, TXT)
- Advanced clause analysis using AI/ML models
- Multi-language document support
- Integration with legal document databases
- Real-time collaboration features
- API endpoints for programmatic access
