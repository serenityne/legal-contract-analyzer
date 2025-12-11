import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const App = () => {
  const [methods, setMethods] = useState([]);
  const [selectedMethod, setSelectedMethod] = useState('bedrock_llm');
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [status, setStatus] = useState({ message: '', progress: '', thinking: '' });
  const [activeTab, setActiveTab] = useState('clauses');
  const [hoveredClause, setHoveredClause] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  // Load available methods on component mount
  useEffect(() => {
    loadMethods();
  }, []);

  const loadMethods = async () => {
    try {
      const response = await axios.get('/api/methods');
      setMethods(response.data.methods);
      
      // Select AI method if available, otherwise local
      const aiMethod = response.data.methods.find(m => m.id === 'bedrock_llm' && m.available);
      if (aiMethod) {
        setSelectedMethod('bedrock_llm');
      } else {
        setSelectedMethod('local');
      }
    } catch (error) {
      console.error('Error loading methods:', error);
    }
  };

  // File drag and drop handlers
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
      } else {
        alert('Please upload a PDF file.');
      }
    }
  }, []);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
      } else {
        alert('Please upload a PDF file.');
      }
    }
  };

  // Simulate real-time status updates
  const updateStatus = (message, progress = '', thinking = '') => {
    setStatus({ message, progress, thinking });
  };

  const analyzeDocument = async () => {
    if (!file) {
      alert('Please select a PDF file first.');
      return;
    }

    setIsProcessing(true);
    setResults(null);
    setActiveTab('clauses');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_method', selectedMethod);

    try {
      // Start with initial status
      updateStatus('Starting document analysis...', '', 'Initializing processing pipeline...');

      // Simulate status updates based on processing method
      if (selectedMethod === 'bedrock_llm') {
        setTimeout(() => updateStatus('Text Extracted: Processing...', 'Document loaded successfully', 'Reading PDF and extracting document text...'), 1000);
        setTimeout(() => updateStatus('AI Processing: Analyzing...', 'Strategy: Parallel processing with 10 AI workers', 'Large document detected. Preparing parallel AI processing...'), 2000);
        setTimeout(() => updateStatus('Claude AI: Extracting clauses...', 'Claude AI: Analyzing document structure and extracting clauses...', 'AI Processing: Connecting to Claude AI for legal document analysis...'), 3000);
        setTimeout(() => updateStatus('AI Simplification: Converting...', 'Claude AI: Generating plain English explanations for all clauses...', 'AI Simplification: Converting legal jargon to plain English...'), 8000);
      } else {
        setTimeout(() => updateStatus('Text Extracted: Ready for analysis', '', 'Reading PDF and extracting text content...'), 500);
        setTimeout(() => updateStatus('Extracting: Pattern recognition...', '', 'Analyzing document structure and identifying clause patterns...'), 1000);
        setTimeout(() => updateStatus('Processing: Categorizing clauses...', '', 'Applying pattern recognition to identify clause types...'), 1500);
      }

      const response = await axios.post('/api/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });

      if (response.data.success) {
        setResults(response.data);
        const clauseCount = response.data.detailed_clauses?.length || 0;
        if (selectedMethod === 'bedrock_llm') {
          updateStatus(`Analysis Complete: ${clauseCount} clauses extracted with plain English explanations`, '', '');
        } else {
          updateStatus(`Analysis Complete: ${clauseCount} clauses extracted and categorized`, '', '');
        }
        
        // Switch to results after a moment
        setTimeout(() => {
          setStatus({ message: '', progress: '', thinking: '' });
        }, 2000);
      } else {
        throw new Error(response.data.error || 'Analysis failed');
      }
    } catch (error) {
      console.error('Error analyzing document:', error);
      updateStatus('', '', '');
      alert(`Error analyzing document: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleClauseHover = (clauseIndex) => {
    setHoveredClause(clauseIndex);
  };

  const renderClausesTab = () => {
    if (!results) {
      return (
        <div style={{ textAlign: 'center', color: '#718096', marginTop: '3rem' }}>
          <i className="fas fa-file-alt" style={{ fontSize: '3rem', marginBottom: '1rem' }}></i>
          <p>Upload and analyze a document to see extracted clauses here.</p>
        </div>
      );
    }

    const clauses = results.detailed_clauses || [];
    const isSimplified = results.processing_metadata?.has_simplification;

    return (
      <div>
        {/* Results Header */}
        <div className="results-header">
          <div className="metric">
            <div className="metric-value">{results.document_info?.text_length?.toLocaleString() || 0}</div>
            <div className="metric-label">Characters</div>
          </div>
          <div className="metric">
            <div className="metric-value">{clauses.length}</div>
            <div className="metric-label">Clauses Found</div>
          </div>
          <div className="metric">
            <div className="metric-value">{results.processing_method?.replace('_', ' ').toUpperCase()}</div>
            <div className="metric-label">Method</div>
          </div>
        </div>

        {/* Clauses List */}
        <div>
          {clauses.map((clause, index) => (
            <ClauseCard 
              key={index} 
              clause={clause} 
              index={index}
              isSimplified={isSimplified}
              onHover={handleClauseHover}
              isHighlighted={hoveredClause === index}
            />
          ))}
        </div>
      </div>
    );
  };

  const renderComparisonTab = () => {
    if (!results) {
      return (
        <div style={{ textAlign: 'center', color: '#718096', marginTop: '3rem' }}>
          <i className="fas fa-columns" style={{ fontSize: '3rem', marginBottom: '1rem' }}></i>
          <p>Upload and analyze a document to see side-by-side comparison here.</p>
        </div>
      );
    }

    const clauses = results.detailed_clauses || [];
    const originalText = results.original_text || '';
    const isSimplified = results.processing_metadata?.has_simplification;

    if (!isSimplified) {
      return (
        <div style={{ textAlign: 'center', color: '#718096', marginTop: '3rem' }}>
          <i className="fas fa-robot" style={{ fontSize: '3rem', marginBottom: '1rem' }}></i>
          <p>Use AI-Powered Analysis to get simplified explanations for side-by-side comparison.</p>
        </div>
      );
    }

    return <PDFViewerComparison originalText={originalText} clauses={clauses} hoveredClause={hoveredClause} onClauseHover={handleClauseHover} />;
  };

  return (
    <div className={`app ${activeTab === 'comparison' && results?.processing_metadata?.has_simplification ? 'comparison-mode' : ''}`}>
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <i className="fas fa-balance-scale" style={{ fontSize: '1.5rem', color: '#667eea' }}></i>
          <div>
            <h1>Legal Document Analyzer</h1>
            <p className="header-subtitle">AI-powered clause extraction with plain English explanations</p>
          </div>
        </div>
      </header>

      <div className="main-container">
        {/* Sidebar */}
        <div className="sidebar">
          <h2>
            <i className="fas fa-cogs"></i>
            Configuration
          </h2>

          {/* Processing Methods */}
          <div className="processing-methods">
            <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: '#4a5568' }}>Processing Method</h3>
            {methods.map((method) => (
              <div
                key={method.id}
                className={`method-card ${selectedMethod === method.id ? 'selected' : ''} ${!method.available ? 'disabled' : ''}`}
                onClick={() => method.available && setSelectedMethod(method.id)}
              >
                <div className="method-name">{method.name}</div>
                <div className="method-description">{method.description}</div>
                <div className="method-speed">{method.speed}</div>
              </div>
            ))}
          </div>

          {/* File Upload */}
          <div className="upload-section">
            <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: '#4a5568' }}>Document Upload</h3>
            
            <div
              className={`dropzone ${dragActive ? 'active' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input').click()}
            >
              <div className="dropzone-icon">
                <i className="fas fa-cloud-upload-alt"></i>
              </div>
              <div className="dropzone-text">
                Drop PDF here or click to browse
              </div>
              <div className="dropzone-hint">
                Maximum file size: 10 MB
              </div>
            </div>

            <input
              id="file-input"
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />

            {file && (
              <div className="file-info">
                <div className="file-name">
                  <i className="fas fa-file-pdf"></i> {file.name}
                </div>
                <div className="file-size">{formatFileSize(file.size)}</div>
              </div>
            )}

            <button
              className="analyze-button"
              onClick={analyzeDocument}
              disabled={!file || isProcessing}
            >
              {isProcessing ? (
                <>
                  <span className="loading-spinner"></span>
                  Analyzing...
                </>
              ) : (
                <>
                  <i className="fas fa-search"></i>
                  Analyze Document
                </>
              )}
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="main-content">
          {/* Status Display */}
          {(status.message || status.progress || status.thinking) && (
            <div className="status-container">
              {status.message && <div className="status-message">{status.message}</div>}
              {status.progress && <div className="progress-message">{status.progress}</div>}
              {status.thinking && <div className="thinking-message">{status.thinking}</div>}
            </div>
          )}

          {/* Tabs */}
          <div className="tabs-container">
            <div className="tab-list">
              <button
                className={`tab ${activeTab === 'clauses' ? 'active' : ''}`}
                onClick={() => setActiveTab('clauses')}
              >
                <i className="fas fa-list"></i>
                Extracted Clauses
              </button>
              <button
                className={`tab ${activeTab === 'comparison' ? 'active' : ''}`}
                onClick={() => setActiveTab('comparison')}
              >
                <i className="fas fa-columns"></i>
                Side-by-Side Comparison
              </button>
            </div>

            <div className="tab-panel">
              {activeTab === 'clauses' && renderClausesTab()}
              {activeTab === 'comparison' && renderComparisonTab()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Clause Card Component
const ClauseCard = ({ clause, index, isSimplified, onHover, isHighlighted }) => {
  const [isExpanded, setIsExpanded] = useState(index === 0); // First clause expanded by default

  return (
    <div 
      className={`clause-card ${isHighlighted ? 'highlighted' : ''}`}
      onMouseEnter={() => onHover(index)}
      onMouseLeave={() => onHover(null)}
    >
      <div className="clause-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="clause-title">
          {isSimplified ? clause.simple_title || clause.clause_name : clause.clause_name}
        </div>
        <i className={`fas fa-chevron-down clause-toggle ${isExpanded ? 'expanded' : ''}`}></i>
      </div>
      
      {isExpanded && (
        <div className="clause-content">
          {isSimplified ? (
            <div>
              {clause.plain_english_summary && (
                <div className="plain-english-summary">
                  <strong>Plain English Summary:</strong>
                  <p>{clause.plain_english_summary}</p>
                </div>
              )}

              {clause.key_points && clause.key_points.length > 0 && (
                <div className="key-points">
                  <h4>Key Points:</h4>
                  <ul>
                    {clause.key_points.map((point, pointIndex) => (
                      <li key={pointIndex}>{point}</li>
                    ))}
                  </ul>
                </div>
              )}

              {clause.potential_impact && (
                <div className="impact-section">
                  <strong>Impact:</strong> {clause.potential_impact}
                </div>
              )}

              {clause.red_flags && (
                <div className={`red-flags ${clause.red_flags.toLowerCase().includes('none') ? 'safe' : 'warning'}`}>
                  <strong>Red Flags:</strong> {clause.red_flags}
                </div>
              )}

              <details style={{ marginTop: '1rem' }}>
                <summary style={{ cursor: 'pointer', color: '#667eea', fontWeight: '500' }}>
                  View Original Legal Text
                </summary>
                <div className="original-text" style={{ marginTop: '0.5rem' }}>
                  {clause.content}
                </div>
              </details>
            </div>
          ) : (
            <div className="original-text">
              {clause.content}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// PDF Viewer Comparison Component with Synchronized Scrolling
const PDFViewerComparison = ({ originalText, clauses, hoveredClause, onClauseHover }) => {
  const leftViewerRef = React.useRef(null);
  const rightViewerRef = React.useRef(null);
  const [selectedClause, setSelectedClause] = useState(null);
  const [isScrollSyncing, setIsScrollSyncing] = useState(false);

  // Synchronized scrolling handler
  const handleScroll = useCallback((sourceRef, targetRef) => {
    if (isScrollSyncing) return;
    
    setIsScrollSyncing(true);
    const sourceElement = sourceRef.current;
    const targetElement = targetRef.current;
    
    if (sourceElement && targetElement) {
      const scrollPercentage = sourceElement.scrollTop / (sourceElement.scrollHeight - sourceElement.clientHeight);
      const targetScrollTop = scrollPercentage * (targetElement.scrollHeight - targetElement.clientHeight);
      
      // Use requestAnimationFrame for smooth scrolling
      requestAnimationFrame(() => {
        targetElement.scrollTop = targetScrollTop;
        setTimeout(() => setIsScrollSyncing(false), 50);
      });
    } else {
      setIsScrollSyncing(false);
    }
  }, [isScrollSyncing]);

  // Highlight clause handler
  const handleClauseClick = (clauseIndex) => {
    setSelectedClause(clauseIndex === selectedClause ? null : clauseIndex);
    onClauseHover(clauseIndex === selectedClause ? null : clauseIndex);
  };

  // Find text in original document for highlighting
  const highlightOriginalText = (text, clauses, selectedClause) => {
    if (!selectedClause || selectedClause < 0 || !clauses[selectedClause]) {
      return text;
    }

    const clause = clauses[selectedClause];
    const clauseContent = clause.content || '';
    
    // Simple highlighting - find the clause content in the original text
    if (clauseContent && text.includes(clauseContent)) {
      return text.replace(
        clauseContent,
        `<span class="clause-highlight selected" id="clause-${selectedClause}">${clauseContent}</span>`
      );
    }

    return text;
  };

  return (
    <div className="comparison-container">
      {/* Original Document Viewer */}
      <div className="comparison-panel">
        <div className="panel-title">
          <i className="fas fa-file-pdf"></i>
          Original Document
        </div>
        <div 
          className="pdf-viewer"
          ref={leftViewerRef}
          onScroll={() => handleScroll(leftViewerRef, rightViewerRef)}
        >
          <div className="document-page">
            <div 
              className="original-text"
              dangerouslySetInnerHTML={{
                __html: highlightOriginalText(originalText, clauses, selectedClause)
              }}
            />
          </div>
          <div className="scroll-indicator">
            <i className="fas fa-sync-alt"></i>
          </div>
        </div>
      </div>

      {/* Simplified Document Viewer */}
      <div className="comparison-panel">
        <div className="panel-title">
          <i className="fas fa-lightbulb"></i>
          Plain English Explanations
        </div>
        <div 
          className="pdf-viewer"
          ref={rightViewerRef}
          onScroll={() => handleScroll(rightViewerRef, leftViewerRef)}
        >
          <div className="simplified-page">
            {clauses.map((clause, index) => (
              <div 
                key={index}
                className={`simplified-clause ${
                  hoveredClause === index ? 'highlighted' : ''
                } ${selectedClause === index ? 'selected' : ''}`}
                onMouseEnter={() => onClauseHover(index)}
                onMouseLeave={() => onClauseHover(null)}
                onClick={() => handleClauseClick(index)}
              >
                <div className="simple-title">
                  {clause.simple_title || clause.clause_name}
                </div>
                
                {clause.plain_english_summary && (
                  <div className="plain-english-summary">
                    <strong>In Plain English:</strong> {clause.plain_english_summary}
                  </div>
                )}

                {clause.key_points && clause.key_points.length > 0 && (
                  <div className="key-points">
                    <h4>Key Points:</h4>
                    <ul>
                      {clause.key_points.map((point, pointIndex) => (
                        <li key={pointIndex}>{point}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {clause.potential_impact && (
                  <div className="impact-section">
                    <strong>What this means for you:</strong> {clause.potential_impact}
                  </div>
                )}

                {clause.red_flags && (
                  <div className={`red-flags ${clause.red_flags.toLowerCase().includes('none') ? 'safe' : 'warning'}`}>
                    <strong>Red Flags:</strong> {clause.red_flags}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="scroll-indicator">
            <i className="fas fa-sync-alt"></i>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
