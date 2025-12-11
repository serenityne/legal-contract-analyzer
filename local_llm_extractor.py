#!/usr/bin/env python3
"""
Local LLM-based clause extractor using Ollama
Fast, reliable, and runs entirely on your machine
"""

import json
import logging
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class SimpleClause:
    """Data class representing a legal clause"""
    clause_name: str
    content: str

class LocalLLMExtractor:
    """Local LLM-based clause extractor using Ollama"""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        """
        Initialize local LLM extractor
        
        Args:
            model_name: Ollama model to use (default: llama3.2:3b for speed)
        """
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
        self._check_ollama_connection()
    
    def _check_ollama_connection(self):
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Ollama is not running")
            
            # Check if model is available
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            if self.model_name not in model_names:
                logger.warning(f"Model {self.model_name} not found. Available models: {model_names}")
                # Try to pull the model
                self._pull_model()
            
            logger.info(f"Successfully connected to Ollama with model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {str(e)}")
            logger.info("To use local LLM processing:")
            logger.info("1. Install Ollama: https://ollama.ai")
            logger.info("2. Run: ollama pull llama3.2:3b")
            logger.info("3. Start Ollama service")
            raise
    
    def _pull_model(self):
        """Pull the model if it's not available"""
        try:
            logger.info(f"Pulling model {self.model_name}...")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model_name},
                timeout=300  # 5 minutes for model download
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully pulled model {self.model_name}")
            else:
                logger.error(f"Failed to pull model: {response.text}")
                
        except Exception as e:
            logger.error(f"Error pulling model: {str(e)}")
            raise
    
    def extract_clauses_with_llm(self, text: str) -> List[SimpleClause]:
        """
        Extract all clauses using local LLM
        
        Args:
            text: Legal document text
            
        Returns:
            List of SimpleClause objects
        """
        try:
            start_time = time.time()
            
            # For large documents, process in chunks
            if len(text) > 8000:  # ~8k chars per chunk for local processing
                logger.info(f"Large document ({len(text)} chars), processing in chunks")
                return self._extract_clauses_chunked(text)
            else:
                # Small document, process normally
                prompt = self._create_clause_extraction_prompt(text)
                response = self._call_local_llm(prompt)
                extracted_clauses = self._parse_llm_response(response)
                
                elapsed = time.time() - start_time
                logger.info(f"Successfully extracted {len(extracted_clauses)} clauses in {elapsed:.1f}s")
                return extracted_clauses
            
        except Exception as e:
            logger.error(f"Error extracting clauses with local LLM: {str(e)}")
            raise
    
    def _extract_clauses_chunked(self, text: str) -> List[SimpleClause]:
        """Process large documents in chunks"""
        try:
            # Split into 8k chunks for local processing
            chunks = self._split_into_chunks(text, max_size=8000)
            logger.info(f"Split document into {len(chunks)} chunks (~8k each)")
            
            all_clauses = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
                
                try:
                    start_time = time.time()
                    prompt = self._create_clause_extraction_prompt(chunk)
                    response = self._call_local_llm(prompt)
                    chunk_clauses = self._parse_llm_response(response)
                    
                    # Add chunk info to clause names for tracking
                    for clause in chunk_clauses:
                        clause.clause_name = f"[Chunk {i+1}] {clause.clause_name}"
                    
                    all_clauses.extend(chunk_clauses)
                    elapsed = time.time() - start_time
                    logger.info(f"Chunk {i+1} extracted {len(chunk_clauses)} clauses in {elapsed:.1f}s")
                    
                except Exception as e:
                    logger.warning(f"Error processing chunk {i+1}: {str(e)}")
                    continue
            
            logger.info(f"Total clauses extracted from all chunks: {len(all_clauses)}")
            return all_clauses
            
        except Exception as e:
            logger.error(f"Error in chunked processing: {str(e)}")
            raise
    
    def _split_into_chunks(self, text: str, max_size: int = 8000) -> List[str]:
        """Split text into chunks while preserving boundaries"""
        try:
            # Try to split on section boundaries first
            import re
            section_pattern = r'\n(?=(?:Section|Article|Clause|SECTION|ARTICLE|CLAUSE|\d+\.)\s)'
            sections = re.split(section_pattern, text)
            
            chunks = []
            current_chunk = ""
            
            for section in sections:
                # If adding this section would exceed max size
                if len(current_chunk) + len(section) > max_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = section
                else:
                    current_chunk += section
            
            # Add the last chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # If chunks are still too large, split by paragraphs
            final_chunks = []
            for chunk in chunks:
                if len(chunk) <= max_size:
                    final_chunks.append(chunk)
                else:
                    # Split large chunks by double newlines
                    paragraphs = chunk.split('\n\n')
                    temp_chunk = ""
                    
                    for para in paragraphs:
                        if len(temp_chunk) + len(para) > max_size and temp_chunk:
                            final_chunks.append(temp_chunk.strip())
                            temp_chunk = para
                        else:
                            temp_chunk += "\n\n" + para if temp_chunk else para
                    
                    if temp_chunk.strip():
                        final_chunks.append(temp_chunk.strip())
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"Error splitting text into chunks: {str(e)}")
            # Fallback: simple character-based splitting
            chunks = []
            for i in range(0, len(text), max_size):
                chunks.append(text[i:i + max_size])
            return chunks
    
    def _create_clause_extraction_prompt(self, text: str) -> str:
        """Create a prompt for local LLM to extract legal clauses"""
        
        prompt = f"""You are a legal expert. Analyze this legal document and extract all distinct clauses, sections, or provisions.

For each clause, provide:
1. Clause name/title 
2. Complete text content

Return ONLY a JSON array in this exact format:
[
  {{
    "clause_name": "Section 1. Definitions",
    "content": "Complete text of the definitions section..."
  }},
  {{
    "clause_name": "Payment Terms", 
    "content": "Complete text of the payment terms..."
  }}
]

Rules:
- Extract meaningful legal provisions, not individual words
- Use original headings when available
- Include full clause text
- Return valid JSON only

Document:
{text}

JSON array:"""

        return prompt
    
    def _call_local_llm(self, prompt: str) -> str:
        """Call local LLM via Ollama API"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 2048  # Max tokens
                }
            }
            
            logger.info(f"Calling local LLM ({self.model_name})")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60  # 1 minute timeout for local processing
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM API error: {response.status_code} - {response.text}")
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Error calling local LLM: {str(e)}")
            raise
    
    def _parse_llm_response(self, response: str) -> List[SimpleClause]:
        """Parse LLM JSON response into SimpleClause objects"""
        try:
            # Extract JSON from response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON array found in LLM response")
            
            json_str = response[start_idx:end_idx]
            parsed_response = json.loads(json_str)
            
            clauses = []
            
            # Convert to SimpleClause objects
            for clause_data in parsed_response:
                if isinstance(clause_data, dict):
                    clause = SimpleClause(
                        clause_name=clause_data.get('clause_name', 'Unnamed Clause'),
                        content=clause_data.get('content', '')
                    )
                    clauses.append(clause)
            
            return clauses
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            logger.debug(f"LLM response was: {response}")
            # Fallback: return empty list instead of failing
            return []
    
    def extract_clauses_by_type(self, text: str, target_clause_types: List[str] = None) -> Dict[str, List[str]]:
        """
        Extract clauses and return in format compatible with existing interface
        
        Args:
            text: Legal document text
            target_clause_types: Not used in LLM approach
            
        Returns:
            Dictionary with "All Clauses" key containing list of clause content
        """
        try:
            clauses = self.extract_clauses_with_llm(text)
            
            result = {
                "All Clauses": [f"{clause.clause_name}\n\n{clause.content}" for clause in clauses]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in extract_clauses_by_type: {str(e)}")
            raise
    
    def get_detailed_clauses(self, text: str) -> List[Dict]:
        """
        Get detailed clause information for display
        
        Returns:
            List of dictionaries with clause details
        """
        try:
            clauses = self.extract_clauses_with_llm(text)
            
            return [
                {
                    'clause_name': clause.clause_name,
                    'content': clause.content,
                    'clause_type': 'Local LLM',
                    'section_number': None,
                    'page_reference': None
                }
                for clause in clauses
            ]
            
        except Exception as e:
            logger.error(f"Error getting detailed clauses: {str(e)}")
            return []
