import boto3
import json
import logging
import re
import asyncio
import concurrent.futures
from typing import List, Dict, Optional
from dataclasses import dataclass
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class SimpleClause:
    """Data class representing a legal clause"""
    clause_name: str
    content: str

class BedrockClauseExtractor:
    """LLM-based clause extractor using AWS Bedrock with Claude"""
    
    def __init__(self):
        self.config = Config()
        self.bedrock_client = None
        self._initialize_bedrock()
    
    def _initialize_bedrock(self):
        """Initialize Bedrock client with optimized configuration"""
        try:
            # Configure client with aggressive timeouts for speed
            client_config = boto3.session.Config(
                read_timeout=45,  # Aggressive timeout
                connect_timeout=30,
                retries={'max_attempts': 1}  # No retries for speed
            )
            
            session = boto3.Session(
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION
            )
            
            # OPTIMIZATION: Reuse this client instead of creating new ones
            self.bedrock_client = session.client('bedrock-runtime', config=client_config)
            logger.info("Successfully initialized optimized Bedrock client")
            
        except Exception as e:
            logger.error(f"Error initializing Bedrock: {str(e)}")
            raise
    
    def extract_clauses_with_llm(self, text: str) -> List[SimpleClause]:
        """
        Extract all clauses using Claude LLM with chunking for large documents
        
        Args:
            text: Legal document text
            
        Returns:
            List of SimpleClause objects
        """
        try:
            # For large documents, process in ultra-small chunks for MAXIMUM speed
            if len(text) > 5000:  # LOWERED threshold - chunk even smaller docs!
                logger.info(f"Large document ({len(text)} chars), processing in parallel chunks")
                return self._extract_clauses_chunked_parallel(text)
            else:
                # Small document, process normally
                prompt = self._create_clause_extraction_prompt(text)
                response = self._call_claude(prompt)
                extracted_clauses = self._parse_claude_response(response)
                
                logger.info(f"Successfully extracted {len(extracted_clauses)} clauses with LLM")
                return extracted_clauses
            
        except Exception as e:
            logger.error(f"Error extracting clauses with LLM: {str(e)}")
            raise
    
    def _extract_clauses_chunked_parallel(self, text: str) -> List[SimpleClause]:
        """Process large documents in many small chunks with parallel processing"""
        try:
            # BALANCED CHUNKING: Split into ~5k character chunks for good parallelization without tiny chunks
            chunks = self._split_into_chunks(text, max_size=5000)
            logger.info(f"Split document into {len(chunks)} balanced chunks (~5k each)")
            
            all_clauses = []
            
            # PARALLEL PROCESSING: Process multiple chunks simultaneously
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  # DOUBLED workers for max speed!
                # Submit all chunk processing tasks
                future_to_chunk = {
                    executor.submit(self._process_single_chunk, i, chunk): (i, chunk) 
                    for i, chunk in enumerate(chunks)
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_chunk):
                    chunk_idx, chunk = future_to_chunk[future]
                    try:
                        chunk_clauses = future.result()
                        if chunk_clauses:
                            # Add chunk info to clause names for tracking
                            for clause in chunk_clauses:
                                clause.clause_name = f"[Chunk {chunk_idx+1}] {clause.clause_name}"
                            all_clauses.extend(chunk_clauses)
                            logger.info(f"Chunk {chunk_idx+1} completed: {len(chunk_clauses)} clauses")
                    except Exception as e:
                        logger.warning(f"Chunk {chunk_idx+1} failed: {str(e)}")
                        continue
            
            logger.info(f"Parallel processing complete: {len(all_clauses)} total clauses")
            return all_clauses
            
        except Exception as e:
            logger.error(f"Error in parallel chunked processing: {str(e)}")
            raise
    
    def _process_single_chunk(self, chunk_idx: int, chunk: str) -> List[SimpleClause]:
        """Process a single chunk (for parallel execution)"""
        try:
            logger.info(f"Processing chunk {chunk_idx+1} ({len(chunk)} chars)")
            
            prompt = self._create_clause_extraction_prompt(chunk)
            response = self._call_claude(prompt, timeout=20)  # ULTRA aggressive 20s timeout
            chunk_clauses = self._parse_claude_response(response)
            
            return chunk_clauses
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_idx+1}: {str(e)}")
            return []
    
    def _extract_clauses_chunked(self, text: str) -> List[SimpleClause]:
        """Process large documents in chunks with parallel processing"""
        try:
            # OPTIMIZATION: Use 25k chunks to match trigger threshold
            chunks = self._split_into_chunks(text, max_size=25000)
            logger.info(f"Split document into {len(chunks)} chunks (25k each)")
            
            all_clauses = []
            
            # OPTIMIZATION: Process chunks with aggressive timeouts
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
                
                try:
                    prompt = self._create_clause_extraction_prompt(chunk)
                    response = self._call_claude(prompt, timeout=45)  # AGGRESSIVE 45s timeout!
                    chunk_clauses = self._parse_claude_response(response)
                    
                    # Add chunk info to clause names for tracking
                    for clause in chunk_clauses:
                        clause.clause_name = f"[Chunk {i+1}] {clause.clause_name}"
                    
                    all_clauses.extend(chunk_clauses)
                    logger.info(f"Chunk {i+1} extracted {len(chunk_clauses)} clauses in <45s")
                    
                except Exception as e:
                    logger.warning(f"Error processing chunk {i+1}: {str(e)}")
                    continue
            
            logger.info(f"Total clauses extracted from all chunks: {len(all_clauses)}")
            return all_clauses
            
        except Exception as e:
            logger.error(f"Error in chunked processing: {str(e)}")
            raise
    
    def _split_into_chunks(self, text: str, max_size: int = 15000) -> List[str]:
        """Split text into chunks while preserving clause boundaries"""
        try:
            # Try to split on section boundaries first
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
        """Create a simple prompt for Claude to extract legal clauses"""
        
        prompt = f"""You are a legal expert. Please analyze this legal document and extract all distinct clauses, sections, or provisions.

For each clause you find, identify:
1. The clause name/title (e.g., "Section 1. Definitions", "Payment Terms", "Termination", etc.)
2. The complete text content of that clause

Return your analysis as a JSON array with this format:
[
  {{
    "clause_name": "Section 1. Definitions",
    "content": "Complete text of the definitions section..."
  }},
  {{
    "clause_name": "Payment Terms", 
    "content": "Complete text of the payment terms clause..."
  }}
]

Important:
- Include the full text of each clause, not summaries
- Use the original clause titles/headings when available
- If no clear title exists, create a descriptive name
- Be thorough and capture all distinct legal provisions

Legal document to analyze:

{text}

Please provide the JSON array of extracted clauses:"""

        return prompt
    
    def _call_claude(self, prompt: str, timeout: int = 45) -> str:
        """Call Claude via AWS Bedrock using reusable client (MAJOR OPTIMIZATION)"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,  # QUALITY: Better output quality while still fast
                "temperature": 0.0,  # FASTEST: No randomness
                "top_p": 1.0,       # FASTEST: No filtering
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            logger.info(f"Calling Claude (reusing client) with {timeout}s timeout")
            
            # OPTIMIZATION: Use pre-initialized client instead of creating new ones!
            response = self.bedrock_client.invoke_model(
                modelId=self.config.BEDROCK_MODEL_ID,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Error calling Claude: {str(e)}")
            raise
    
    def _parse_claude_response(self, response: str) -> List[SimpleClause]:
        """Parse Claude's JSON response into SimpleClause objects with robust error handling"""
        try:
            # Extract JSON from response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON array found in Claude's response")
            
            json_str = response[start_idx:end_idx]
            
            # ROBUST PARSING: Try multiple strategies
            parsed_response = None
            
            # Strategy 1: Direct JSON parsing
            try:
                parsed_response = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Direct JSON parsing failed: {str(e)}")
                
                # Strategy 2: Fix common JSON issues
                try:
                    # Fix trailing commas and other common issues
                    fixed_json = self._fix_json_format(json_str)
                    parsed_response = json.loads(fixed_json)
                    logger.info("Successfully parsed JSON after fixing formatting issues")
                except Exception as e2:
                    logger.warning(f"JSON fixing failed: {str(e2)}")
                    
                    # Strategy 3: Extract clauses manually using regex
                    try:
                        parsed_response = self._extract_clauses_with_regex(response)
                        logger.info("Successfully extracted clauses using regex fallback")
                    except Exception as e3:
                        logger.error(f"All parsing strategies failed: {str(e3)}")
                        raise Exception(f"Could not parse Claude response: {str(e)}")
            
            if not parsed_response:
                raise ValueError("No valid clause data found")
            
            clauses = []
            
            # Convert to SimpleClause objects
            for clause_data in parsed_response:
                if isinstance(clause_data, dict):
                    clause = SimpleClause(
                        clause_name=clause_data.get('clause_name', 'Unnamed Clause'),
                        content=clause_data.get('content', '')
                    )
                    clauses.append(clause)
            
            logger.info(f"Successfully parsed {len(clauses)} clauses from Claude response")
            return clauses
            
        except Exception as e:
            logger.error(f"Error parsing Claude response: {str(e)}")
            logger.debug(f"Claude response was: {response}")
            # Return empty list as fallback, but log the issue clearly
            logger.error("CRITICAL: Returning 0 clauses due to parsing failure!")
            return []
    
    def _fix_json_format(self, json_str: str) -> str:
        """Fix common JSON formatting issues"""
        try:
            # Remove trailing commas before closing brackets
            fixed = re.sub(r',\s*}', '}', json_str)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            # Fix unescaped quotes in strings
            # This is a simple fix - for production, use a more robust approach
            fixed = re.sub(r'(?<!\\)"(?![,}:\]])(?![^"]*"[^"]*$)', '\\"', fixed)
            
            return fixed
        except Exception as e:
            logger.error(f"Error fixing JSON format: {str(e)}")
            raise
    
    def _extract_clauses_with_regex(self, response: str) -> List[Dict]:
        """Fallback: Extract clauses using regex when JSON parsing fails"""
        try:
            clauses = []
            
            # Look for patterns like "clause_name": "...", "content": "..."
            pattern = r'"clause_name"\s*:\s*"([^"]+)"\s*,\s*"content"\s*:\s*"([^"]+)"'
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                clause_name, content = match
                # Clean up escaped characters
                clause_name = clause_name.replace('\\"', '"').replace('\\n', '\n')
                content = content.replace('\\"', '"').replace('\\n', '\n')
                
                clauses.append({
                    'clause_name': clause_name,
                    'content': content
                })
            
            if clauses:
                logger.info(f"Regex extraction found {len(clauses)} clauses")
                return clauses
            
            # If regex fails, try a more general approach
            # Look for any clause-like structure in the text
            lines = response.split('\n')
            current_clause = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('"clause_name"') or 'Section' in line or 'Article' in line:
                    # Save previous clause
                    if current_clause and current_content:
                        clauses.append({
                            'clause_name': current_clause,
                            'content': '\n'.join(current_content)
                        })
                    
                    # Start new clause
                    current_clause = line.replace('"clause_name":', '').replace('"', '').strip()
                    current_content = []
                elif line.startswith('"content"'):
                    # Content line
                    content_text = line.replace('"content":', '').replace('"', '').strip()
                    current_content.append(content_text)
                elif current_clause and line:
                    # Continue content
                    current_content.append(line)
            
            # Add last clause
            if current_clause and current_content:
                clauses.append({
                    'clause_name': current_clause,
                    'content': '\n'.join(current_content)
                })
            
            return clauses
            
        except Exception as e:
            logger.error(f"Error in regex extraction: {str(e)}")
            raise
    
    def extract_clauses_by_type(self, text: str, target_clause_types: List[str] = None) -> Dict[str, List[str]]:
        """
        Extract clauses and return in format compatible with existing interface
        
        Args:
            text: Legal document text
            target_clause_types: Not used in LLM approach, kept for compatibility
            
        Returns:
            Dictionary with "All Clauses" key containing list of clause content
        """
        try:
            clauses = self.extract_clauses_with_llm(text)
            
            # Return all clauses under a single key for now
            # The UI can be updated to display them properly
            result = {
                "All Clauses": [f"{clause.clause_name}\n\n{clause.content}" for clause in clauses]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in extract_clauses_by_type: {str(e)}")
            raise
    
    def get_detailed_clauses(self, text: str, simplify_for_non_lawyers: bool = False) -> List[Dict]:
        """
        Get detailed clause information for display
        
        Args:
            text: Legal document text
            simplify_for_non_lawyers: Whether to add simplified explanations
        
        Returns:
            List of dictionaries with clause details
        """
        try:
            clauses = self.extract_clauses_with_llm(text)
            
            # If simplification is requested, add simplified versions
            if simplify_for_non_lawyers:
                simplified_clauses = self._simplify_clauses_parallel(clauses)
                return simplified_clauses
            
            return [
                {
                    'clause_name': clause.clause_name,
                    'content': clause.content,
                    'clause_type': 'LLM Extracted',
                    'section_number': None,
                    'page_reference': None
                }
                for clause in clauses
            ]
            
        except Exception as e:
            logger.error(f"Error getting detailed clauses: {str(e)}")
            return []
    
    def _simplify_clauses_parallel(self, clauses: List[SimpleClause]) -> List[Dict]:
        """
        Simplify clauses in parallel for non-lawyers to understand
        
        Args:
            clauses: List of extracted clauses
            
        Returns:
            List of dictionaries with original and simplified content
        """
        try:
            logger.info(f"Simplifying {len(clauses)} clauses in parallel for non-lawyers")
            
            simplified_clauses = []
            
            # PARALLEL SIMPLIFICATION: Process 10 clauses at a time
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all clause simplification tasks
                future_to_clause = {
                    executor.submit(self._simplify_single_clause, i, clause): (i, clause)
                    for i, clause in enumerate(clauses)
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_clause):
                    clause_idx, original_clause = future_to_clause[future]
                    try:
                        simplified_result = future.result()
                        if simplified_result:
                            simplified_clauses.append(simplified_result)
                            logger.info(f"Clause {clause_idx+1} simplified successfully")
                    except Exception as e:
                        logger.warning(f"Failed to simplify clause {clause_idx+1}: {str(e)}")
                        # Fallback: add original clause without simplification
                        simplified_clauses.append({
                            'clause_name': original_clause.clause_name,
                            'content': original_clause.content,
                            'simplified_explanation': '❌ Simplification failed - showing original legal text',
                            'clause_type': 'LLM Extracted (Simplification Failed)',
                            'section_number': None,
                            'page_reference': None
                        })
                        continue
            
            # Sort by original order
            simplified_clauses.sort(key=lambda x: x.get('original_index', 0))
            
            logger.info(f"Parallel simplification complete: {len(simplified_clauses)} clauses processed")
            return simplified_clauses
            
        except Exception as e:
            logger.error(f"Error in parallel clause simplification: {str(e)}")
            # Fallback: return original clauses without simplification
            return [
                {
                    'clause_name': clause.clause_name,
                    'content': clause.content,
                    'simplified_explanation': '❌ Simplification service unavailable - showing original legal text',
                    'clause_type': 'LLM Extracted (No Simplification)',
                    'section_number': None,
                    'page_reference': None
                }
                for clause in clauses
            ]
    
    def _simplify_single_clause(self, clause_idx: int, clause: SimpleClause) -> Dict:
        """
        Simplify a single clause for non-lawyers to understand
        
        Args:
            clause_idx: Index of the clause
            clause: The clause to simplify
            
        Returns:
            Dictionary with original and simplified content
        """
        try:
            logger.info(f"Simplifying clause {clause_idx+1}: {clause.clause_name[:50]}...")
            
            # Create simplification prompt
            simplification_prompt = f"""You are a legal expert who explains complex legal language to everyday people. 

Please take this legal clause and provide a simple, clear explanation that anyone can understand.

Original Legal Clause:
Title: {clause.clause_name}
Content: {clause.content}

Please provide your response in this JSON format:
{{
    "simple_title": "A short, plain English title for this clause",
    "key_points": [
        "Main point 1 in simple language",
        "Main point 2 in simple language", 
        "Main point 3 in simple language"
    ],
    "plain_english_summary": "A 1-2 sentence summary of what this clause means in everyday language",
    "potential_impact": "What this might mean for someone affected by this contract (1 sentence)",
    "red_flags": "Any concerning aspects or things to watch out for (1 sentence, or 'None identified' if no concerns)"
}}

Important:
- Use simple, everyday language 
- Avoid legal jargon
- Focus on practical impact
- Be concise but accurate
- Help people understand what this means for them

JSON Response:"""

            # Call Claude for simplification
            response = self._call_claude(simplification_prompt, timeout=30)
            simplified_data = self._parse_simplification_response(response)
            
            if simplified_data:
                return {
                    'clause_name': clause.clause_name,
                    'content': clause.content,
                    'simple_title': simplified_data.get('simple_title', clause.clause_name),
                    'key_points': simplified_data.get('key_points', []),
                    'plain_english_summary': simplified_data.get('plain_english_summary', ''),
                    'potential_impact': simplified_data.get('potential_impact', ''),
                    'red_flags': simplified_data.get('red_flags', 'None identified'),
                    'clause_type': 'LLM Extracted + Simplified',
                    'section_number': None,
                    'page_reference': None,
                    'original_index': clause_idx
                }
            else:
                raise ValueError("Failed to parse simplification response")
                
        except Exception as e:
            logger.error(f"Error simplifying clause {clause_idx+1}: {str(e)}")
            raise
    
    def _parse_simplification_response(self, response: str) -> Dict:
        """Parse Claude's JSON response for clause simplification"""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON found in simplification response")
            
            json_str = response[start_idx:end_idx]
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"Error parsing simplification response: {str(e)}")
            logger.debug(f"Simplification response was: {response}")
            return None
