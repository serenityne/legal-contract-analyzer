import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import ChatInterface from './ChatInterface';

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
  const [cachedResults, setCachedResults] = useState({});

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

    // Check cache first
    const cacheKey = `${file.name}_${file.size}_${selectedMethod}`;
    if (cachedResults[cacheKey]) {
      console.log('Using cached results for:', file.name);
      setResults(cachedResults[cacheKey]);
      updateStatus('Using cached analysis results', '', '');
      setTimeout(() => {
        setStatus({ message: '', progress: '', thinking: '' });
      }, 1500);
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
        
        // Cache the results
        const newCacheKey = `${file.name}_${file.size}_${selectedMethod}`;
        setCachedResults(prev => ({
          ...prev,
          [newCacheKey]: response.data
        }));
        
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

  const renderRisksTab = () => {
    if (!results) {
      return (
        <div style={{ textAlign: 'center', color: '#718096', marginTop: '3rem' }}>
          <i className="fas fa-shield-alt" style={{ fontSize: '3rem', marginBottom: '1rem' }}></i>
          <p>Upload and analyze a document to see risk assessment here.</p>
        </div>
      );
    }

    const riskAssessment = results.risk_assessment;
    const isAIPowered = results.processing_method === 'bedrock_llm';

    // Debug logging
    console.log('Risk Tab Debug:', {
      processing_method: results.processing_method,
      isAIPowered,
      has_risk_assessment: riskAssessment,
      risk_data: riskAssessment
    });

    if (!isAIPowered) {
      return (
        <div style={{ textAlign: 'center', color: '#718096', marginTop: '3rem' }}>
          <i className="fas fa-robot" style={{ fontSize: '3rem', marginBottom: '1rem' }}></i>
          <p>Use AI-Powered Analysis to get detailed risk assessment.</p>
        </div>
      );
    }

    return <RiskAnalysis riskAssessment={riskAssessment} />;
  };

  return (
    <div className="app">
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

      <div className={`main-container ${results ? 'with-results' : ''}`}>
        {/* Sidebar - Hide after results */}
        {!results && (
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
        )}

        {/* Main Content - Full width when results available */}
        <div className={`main-content ${results ? 'with-chat' : ''}`}>
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
              <button
                className={`tab ${activeTab === 'risks' ? 'active' : ''}`}
                onClick={() => setActiveTab('risks')}
              >
                <i className="fas fa-exclamation-triangle"></i>
                Risk Analysis
              </button>
            </div>

            <div className="tab-panel">
              {activeTab === 'clauses' && renderClausesTab()}
              {activeTab === 'comparison' && renderComparisonTab()}
              {activeTab === 'risks' && renderRisksTab()}
            </div>
          </div>
        </div>

        {/* Chat Interface - Show only when results are available */}
        {results && (
          <div className="chat-panel">
            <ChatInterface 
              documentContext={results}
              documentInfo={results.document_info}
            />
          </div>
        )}
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

// Clean Side-by-Side Comparison Component (Like Mockup)
const PDFViewerComparison = ({ originalText, clauses, hoveredClause, onClauseHover }) => {
  const leftViewerRef = React.useRef(null);
  const rightViewerRef = React.useRef(null);
  const [selectedClause, setSelectedClause] = useState(null);

  // Simple clause hover handler
  const handleClauseHover = (clauseIndex) => {
    onClauseHover(clauseIndex);
  };

  // Simple clause click handler
  const handleClauseClick = (clauseIndex) => {
    setSelectedClause(clauseIndex === selectedClause ? null : clauseIndex);
    onClauseHover(clauseIndex === selectedClause ? null : clauseIndex);
  };

  return (
    <div className="comparison-container">
      {/* Original Document Panel */}
      <div className="comparison-panel">
        <div className="panel-header">
          Original Document
        </div>
        <div className="panel-content" ref={leftViewerRef}>
          {clauses.map((clause, index) => (
            <div
              key={index}
              className={`clause-box original-clause ${
                hoveredClause === index ? 'hovered' : ''
              } ${selectedClause === index ? 'selected' : ''}`}
              data-clause-index={index}
              onMouseEnter={() => handleClauseHover(index)}
              onMouseLeave={() => handleClauseHover(null)}
              onClick={() => handleClauseClick(index)}
            >
              <div className="clause-header">
                Clause {index + 1} - {clause.clause_name || `Section ${index + 1}`}
              </div>
              <div className="clause-body">
                {clause.content}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Simplified Document Panel */}
      <div className="comparison-panel">
        <div className="panel-header">
          Simplified Document  
        </div>
        <div className="panel-content" ref={rightViewerRef}>
          {clauses.map((clause, index) => (
            <div
              key={index}
              className={`clause-box simplified-clause ${
                hoveredClause === index ? 'hovered' : ''
              } ${selectedClause === index ? 'selected' : ''}`}
              data-clause-index={index}
              onMouseEnter={() => handleClauseHover(index)}
              onMouseLeave={() => handleClauseHover(null)}
              onClick={() => handleClauseClick(index)}
            >
              <div className="clause-header">
                Clause {index + 1} - Simple Summary
              </div>
              <div className="clause-body">
                {clause.plain_english_summary && (
                  <div className="summary">
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
                  <div className="impact">
                    <strong>Impact:</strong> {clause.potential_impact}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Risk Analysis Component
const RiskAnalysis = ({ riskAssessment }) => {
  // Debug what we're receiving
  console.log('RiskAnalysis Component received:', riskAssessment);
  
  const getRiskColor = (riskLevel) => {
    if (riskLevel >= 76) return '#e53e3e'; // Critical - Red
    if (riskLevel >= 51) return '#dd6b20'; // High - Orange  
    if (riskLevel >= 26) return '#d69e2e'; // Moderate - Yellow
    return '#38a169'; // Low - Green
  };

  const getRiskCategory = (riskLevel) => {
    if (riskLevel >= 76) return 'Critical Risk';
    if (riskLevel >= 51) return 'High Risk';
    if (riskLevel >= 26) return 'Moderate Risk';
    return 'Low Risk';
  };

  const overallRisk = riskAssessment?.overall_risk_level || 0;
  const risks = riskAssessment?.risks || [];
  const totalRisks = riskAssessment?.total_risks || 0;
  const highestRisk = riskAssessment?.highest_risk || 0;

  console.log('Risk metrics:', { overallRisk, risks, totalRisks, highestRisk });

  return (
    <div className="risk-analysis">
      {/* Overall Risk Header */}
      <div className="risk-header">
        <div className="overall-risk-card">
          <div className="overall-risk-title">
            <i className="fas fa-shield-alt"></i>
            Overall Document Risk
          </div>
          <div className="overall-risk-score" style={{ color: getRiskColor(overallRisk) }}>
            {overallRisk}%
          </div>
          <div className="overall-risk-category" style={{ color: getRiskColor(overallRisk) }}>
            {getRiskCategory(overallRisk)}
          </div>
          <div className="risk-progress-bar">
            <div 
              className="risk-progress-fill"
              style={{ 
                width: `${overallRisk}%`,
                backgroundColor: getRiskColor(overallRisk)
              }}
            ></div>
          </div>
        </div>

        <div className="risk-metrics">
          <div className="risk-metric">
            <div className="risk-metric-value">{totalRisks}</div>
            <div className="risk-metric-label">Risky Clauses</div>
          </div>
          <div className="risk-metric">
            <div className="risk-metric-value">{highestRisk}%</div>
            <div className="risk-metric-label">Highest Risk</div>
          </div>
          <div className="risk-metric">
            <div className="risk-metric-value">{risks.filter(r => r.risk_level >= 76).length}</div>
            <div className="risk-metric-label">Critical</div>
          </div>
        </div>
      </div>

      {/* Risk Cards */}
      <div className="risk-cards">
        {risks.length === 0 ? (
          <div className="no-risks">
            <i className="fas fa-check-circle" style={{ color: '#38a169', fontSize: '3rem', marginBottom: '1rem' }}></i>
            <h3>No Significant Risks Identified</h3>
            <p>The AI analysis found no clauses with significant risk levels in this document.</p>
          </div>
        ) : (
          risks.map((risk, index) => (
            <div key={index} className="risk-card">
              <div className="risk-card-header">
                <div className="risk-info">
                  <div className="risk-title">{risk.clause_name}</div>
                  <div className="risk-category" style={{ color: getRiskColor(risk.risk_level) }}>
                    {risk.risk_category}
                  </div>
                </div>
                <div className="risk-score">
                  <div className="risk-percentage" style={{ color: getRiskColor(risk.risk_level) }}>
                    {risk.risk_level}%
                  </div>
                  <div className="risk-bar">
                    <div 
                      className="risk-bar-fill"
                      style={{ 
                        width: `${risk.risk_level}%`,
                        backgroundColor: getRiskColor(risk.risk_level)
                      }}
                    ></div>
                  </div>
                </div>
              </div>

              <div className="risk-content">
                {risk.context && (
                  <div className="risk-section">
                    <strong>Context:</strong> {risk.context}
                  </div>
                )}

                {risk.risky_statement && (
                  <div className="risk-section risky-statement">
                    <strong>Risky Statement:</strong> 
                    <div className="highlighted-text">"{risk.risky_statement}"</div>
                  </div>
                )}

                {risk.risk_reasoning && (
                  <div className="risk-section">
                    <strong>Why This Is Risky:</strong> {risk.risk_reasoning}
                  </div>
                )}

                {risk.potential_consequences && (
                  <div className="risk-section consequences">
                    <strong>Potential Consequences:</strong> {risk.potential_consequences}
                  </div>
                )}

                {risk.recommendations && (
                  <div className="risk-section recommendations">
                    <strong>Recommendations:</strong> {risk.recommendations}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default App;
