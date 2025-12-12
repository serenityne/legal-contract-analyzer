import json
import boto3
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BedrockChatbot:
    """Chatbot powered by AWS Bedrock for document Q&A"""
    
    def __init__(self):
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'
        )
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    def generate_response(
        self, 
        question: str, 
        document_context: str,
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Generate a response to user's question based on document context
        
        Args:
            question: User's question
            document_context: The analyzed document content
            chat_history: Previous chat messages
            
        Returns:
            AI-generated response
        """
        try:
            # Build conversation history
            messages = []
            
            # Add chat history if exists, ensuring first message is from user
            if chat_history and len(chat_history) > 0:
                # Filter to get only last few messages
                recent_history = chat_history[-4:]  # Keep last 4 to leave room for current question
                
                # Find first user message in history or start fresh
                first_user_idx = -1
                for i, msg in enumerate(recent_history):
                    if msg.get("role") == "user":
                        first_user_idx = i
                        break
                
                # Only add history starting from first user message
                if first_user_idx >= 0:
                    for msg in recent_history[first_user_idx:]:
                        role = "user" if msg.get("role") == "user" else "assistant"
                        messages.append({
                            "role": role,
                            "content": msg.get("content", "")
                        })
            
            # Ensure we always have current question as user message
            # If messages is empty or last message is from user, add current question
            # Otherwise add current question
            messages.append({
                "role": "user",
                "content": question
            })
            
            # Add system context
            system_prompt = f"""You are a helpful legal document assistant. You have access to a legal document that has been analyzed.

Document Context:
{document_context[:3000]}  # Limit context to avoid token limits

Your role is to:
1. Answer questions about the document accurately
2. Explain legal terms in plain English
3. Highlight important clauses or risks
4. Provide helpful insights about the document
5. Be conversational but professional

If asked about specific clauses, refer to them by their clause names/numbers.
If the question is outside the document's scope, politely redirect to the document content."""
            
            # Prepare the request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "system": system_prompt,
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            # Invoke the model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            answer = response_body.get('content', [{}])[0].get('text', 'I apologize, but I couldn\'t generate a response.')
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}. Please try rephrasing your question."
    
    def suggest_questions(self, document_context: str) -> List[str]:
        """
        Generate suggested questions based on the document
        
        Args:
            document_context: The analyzed document content
            
        Returns:
            List of suggested questions
        """
        try:
            prompt = f"""Based on this legal document summary, suggest 4 relevant questions a user might ask.
Make them specific and helpful.

Document Summary:
{document_context[:1500]}

Format your response as a JSON array of strings, like:
["Question 1", "Question 2", "Question 3", "Question 4"]"""

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.8
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            text = response_body.get('content', [{}])[0].get('text', '[]')
            
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
                return suggestions[:4]
            
            # Fallback suggestions
            return [
                "What are the main obligations in this contract?",
                "Are there any risky clauses I should be aware of?",
                "What is the termination process?",
                "Can you summarize the key points?"
            ]
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return [
                "What are the key terms in this document?",
                "What risks should I be aware of?",
                "Can you explain the main clauses?",
                "What are my obligations under this agreement?"
            ]
