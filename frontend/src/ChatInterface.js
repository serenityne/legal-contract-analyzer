import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const ChatInterface = ({ documentContext, documentInfo }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Load suggestions when component mounts
    if (documentContext) {
      loadSuggestions();
      // Add welcome message
      setMessages([{
        role: 'assistant',
        content: `Hello! I'm your AI legal assistant. I've analyzed the document "${documentInfo?.filename || 'your document'}". Feel free to ask me any questions about it, such as specific clauses, risks, obligations, or anything else you'd like to understand better.`
      }]);
    }
  }, [documentContext]);

  useEffect(() => {
    // Auto-scroll to bottom when messages update
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSuggestions = async () => {
    try {
      const response = await axios.post('/api/chat/suggestions', {
        document_context: documentContext.slice(0, 2000) // Send first 2000 chars for context
      });
      
      if (response.data.success) {
        setSuggestions(response.data.suggestions);
      }
    } catch (error) {
      console.error('Error loading suggestions:', error);
      // Use default suggestions
      setSuggestions([
        "What are the key terms?",
        "Are there any risks?",
        "Explain the main clauses",
        "What are my obligations?"
      ]);
    }
  };

  const sendMessage = async (message = null) => {
    const messageToSend = message || inputMessage;
    if (!messageToSend.trim()) return;

    // Add user message to chat
    const userMessage = { role: 'user', content: messageToSend };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Prepare context - include clause summaries
      const contextSummary = prepareDocumentContext();
      
      const response = await axios.post('/api/chat', {
        question: messageToSend,
        document_context: contextSummary,
        chat_history: messages.slice(-10) // Send last 10 messages for context
      });

      if (response.data.success) {
        const assistantMessage = {
          role: 'assistant',
          content: response.data.response
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'I apologize, but I encountered an error. Please try again or rephrase your question.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const prepareDocumentContext = () => {
    // Create a concise summary of the document for the AI
    let context = `Document: ${documentInfo?.filename || 'Legal Document'}\n\n`;
    
    // Add clause summaries if available
    if (documentContext && typeof documentContext === 'object') {
      if (documentContext.detailed_clauses) {
        context += "Clauses:\n";
        documentContext.detailed_clauses.forEach((clause, idx) => {
          context += `${idx + 1}. ${clause.clause_name || clause.simple_title}: `;
          if (clause.plain_english_summary) {
            context += clause.plain_english_summary.slice(0, 100) + "...\n";
          } else {
            context += clause.content.slice(0, 100) + "...\n";
          }
        });
      }
      
      // Add risk summary if available
      if (documentContext.risk_assessment) {
        context += `\nRisk Assessment: Overall risk ${documentContext.risk_assessment.overall_risk_level}%\n`;
        if (documentContext.risk_assessment.risks) {
          context += "Key risks: ";
          documentContext.risk_assessment.risks.slice(0, 3).forEach(risk => {
            context += `${risk.clause_name} (${risk.risk_level}%), `;
          });
        }
      }
    } else if (typeof documentContext === 'string') {
      // If it's just text, use first part
      context += documentContext.slice(0, 3000);
    }
    
    return context;
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <i className="fas fa-robot"></i>
        <span>AI Legal Assistant</span>
      </div>

      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? (
                <i className="fas fa-user"></i>
              ) : (
                <i className="fas fa-robot"></i>
              )}
            </div>
            <div className="message-content">
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <div className="message-avatar">
              <i className="fas fa-robot"></i>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {suggestions.length > 0 && messages.length <= 1 && (
        <div className="chat-suggestions">
          <div className="suggestions-title">Suggested Questions:</div>
          <div className="suggestions-list">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                className="suggestion-chip"
                onClick={() => sendMessage(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="chat-input-container">
        <input
          type="text"
          className="chat-input"
          placeholder="Ask about the document..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading}
        />
        <button
          className="chat-send-button"
          onClick={() => sendMessage()}
          disabled={isLoading || !inputMessage.trim()}
        >
          <i className="fas fa-paper-plane"></i>
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;
