from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json
import logging
from typing import Dict, List, Optional
import io

# Import our existing modules
from config import Config, setup_logging
from pdf_processor import PDFProcessor
from bedrock_clause_extractor import BedrockClauseExtractor
from clause_extractor import ClauseExtractor
from bedrock_chat import BedrockChatbot

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Legal Document Analyzer API",
    description="API for analyzing legal documents and extracting clauses with AI simplification",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files mounting disabled for development (React dev server handles this)
# app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

# Initialize components
config = Config()
pdf_processor = PDFProcessor(config.MAX_PDF_SIZE_MB)
clause_extractor = ClauseExtractor()

try:
    bedrock_extractor = BedrockClauseExtractor()
    chatbot = BedrockChatbot()
except Exception as e:
    bedrock_extractor = None
    chatbot = None
    logger.warning(f"Bedrock services not available: {str(e)}")

# Request models
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    question: str
    document_context: str
    chat_history: Optional[List[Dict[str, str]]] = None

class SuggestionsRequest(BaseModel):
    document_context: str

@app.get("/")
async def read_root():
    return {"message": "Legal Document Analyzer API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "bedrock_available": bedrock_extractor is not None,
        "services": {
            "pdf_processor": True,
            "clause_extractor": True,
            "bedrock_llm": bedrock_extractor is not None
        }
    }

@app.post("/api/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    processing_method: str = "bedrock_llm"
):
    """
    Analyze a PDF document and extract clauses with AI simplification
    
    Args:
        file: PDF file to analyze
        processing_method: 'local' or 'bedrock_llm'
    
    Returns:
        JSON with extracted clauses and simplified explanations
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read PDF content
        pdf_content = await file.read()
        
        # Extract text from PDF
        text = pdf_processor.extract_text_from_bytes(pdf_content)
        
        if processing_method == "bedrock_llm" and bedrock_extractor:
            # Use Bedrock LLM with automatic simplification
            logger.info(f"Processing with Bedrock LLM: {len(text)} characters")
            
            # Extract clauses with AI
            extracted_clauses = bedrock_extractor.extract_clauses_by_type(text)
            
            # Get detailed clauses with simplification and risk assessment
            result = bedrock_extractor.get_detailed_clauses_with_risks(text, simplify_for_non_lawyers=True)
            detailed_clauses = result.get('detailed_clauses', [])
            risk_assessment = result.get('risk_assessment', {})
            
            return JSONResponse({
                "success": True,
                "processing_method": "bedrock_llm",
                "document_info": {
                    "filename": file.filename,
                    "file_size": len(pdf_content),
                    "text_length": len(text),
                    "total_clauses_found": len(detailed_clauses)
                },
                "original_text": text,
                "extracted_clauses": extracted_clauses,
                "detailed_clauses": detailed_clauses,
                "risk_assessment": risk_assessment,
                "processing_metadata": {
                    "extraction_method": "bedrock_claude_llm_simplified",
                    "total_clauses_found": len(detailed_clauses),
                    "has_simplification": True,
                    "has_risk_assessment": True
                }
            })
            
        else:
            # Use local regex processing
            logger.info(f"Processing locally: {len(text)} characters")
            
            # Extract clauses with regex
            clause_types = config.CLAUSE_TYPES
            extracted_clauses = clause_extractor.extract_clauses_by_type(text, clause_types)
            
            # Get detailed clauses
            detailed_clauses = clause_extractor.split_into_clauses(text)
            grouped_detailed = clause_extractor.group_clauses_by_type(detailed_clauses)
            
            # Convert to API format
            formatted_clauses = []
            for clause_type, clauses in grouped_detailed.items():
                for clause in clauses:
                    formatted_clauses.append({
                        'clause_name': clause.clause_name,
                        'content': clause.content,
                        'clause_type': clause_type,
                        'section_number': clause.section_number,
                        'page_reference': clause.page_reference
                    })
            
            return JSONResponse({
                "success": True,
                "processing_method": "local",
                "document_info": {
                    "filename": file.filename,
                    "file_size": len(pdf_content),
                    "text_length": len(text),
                    "total_clauses_found": len(formatted_clauses)
                },
                "original_text": text,
                "extracted_clauses": extracted_clauses,
                "detailed_clauses": formatted_clauses,
                "processing_metadata": {
                    "extraction_method": "regex_deterministic_local",
                    "total_clauses_found": len(formatted_clauses),
                    "has_simplification": False
                }
            })
            
    except Exception as e:
        logger.error(f"Error analyzing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/api/methods")
async def get_available_methods():
    """Get available processing methods"""
    methods = []
    
    if bedrock_extractor:
        methods.append({
            "id": "bedrock_llm", 
            "name": "AI-Powered Analysis",
            "description": "Advanced AI with plain English explanations and risk assessment",
            "available": True,
            "speed": "Moderate (30-60s)",
            "features": [
                "AI clause extraction", 
                "Plain English summaries",
                "Key points identification",
                "Risk analysis",
                "Impact assessment"
            ]
        })
    else:
        methods.append({
            "id": "bedrock_llm",
            "name": "AI-Powered Analysis", 
            "description": "Advanced AI analysis (requires AWS setup)",
            "available": False,
            "speed": "N/A",
            "features": ["Requires AWS Bedrock configuration"]
        })
    
    return {"methods": methods}

@app.post("/api/chat")
async def chat_with_document(request: ChatRequest):
    """Chat with AI about the analyzed document"""
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot service not available")
    
    try:
        response = chatbot.generate_response(
            question=request.question,
            document_context=request.document_context,
            chat_history=request.chat_history
        )
        
        return JSONResponse({
            "success": True,
            "response": response
        })
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.post("/api/chat/suggestions")
async def get_chat_suggestions(request: SuggestionsRequest):
    """Get suggested questions for the document"""
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot service not available")
    
    try:
        suggestions = chatbot.suggest_questions(request.document_context)
        
        return JSONResponse({
            "success": True,
            "suggestions": suggestions
        })
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        # Return default suggestions on error
        return JSONResponse({
            "success": True,
            "suggestions": [
                "What are the key terms in this document?",
                "What risks should I be aware of?",
                "Can you explain the main clauses?",
                "What are my obligations?"
            ]
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
