import { useState } from 'react';
import '@/App.css';
import axios from 'axios';
import { FileText, Scale, Users, Shield, Upload, Play, CheckCircle, AlertCircle } from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { toast } from 'sonner';
import Auth from '@/components/Auth';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [user, setUser] = useState(null);
  const [files, setFiles] = useState([]);
  const [caseId, setCaseId] = useState(null);
  const [rawText, setRawText] = useState('');
  const [caseDetails, setCaseDetails] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [simulation, setSimulation] = useState(null);
  const [audit, setAudit] = useState(null);
  const [jurisdiction, setJurisdiction] = useState('India');
  const [relatedLaws, setRelatedLaws] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState('upload');
  const [dragging, setDragging] = useState(false);

  // Handle login success
  const handleLoginSuccess = (userData) => {
    setUser(userData);
  };

  // Handle logout
  const handleLogout = () => {
    setUser(null);
    handleReset();
    toast.success('Logged out successfully');
  };

  // If user not logged in, show auth page
  if (!user) {
    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }

  // File upload handlers
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 0) {
      setFiles(prev => [...prev, ...selectedFiles]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files || []);
    if (droppedFiles.length > 0) {
      setFiles(prev => [...prev, ...droppedFiles]);
    }
  };

  // Upload document
  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Please select at least one file');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    
    // Add all files to form data
    files.forEach(file => {
      formData.append('files', file);
    });
    
    // Include selected jurisdiction with upload so it persists with the case
    if (jurisdiction) formData.append('jurisdiction', jurisdiction);

    try {
      const response = await axios.post(`${API}/upload`, formData);
      setCaseId(response.data.case_id);
      setRawText(response.data.raw_text);
      setCurrentStep('process');
      toast.success(`${response.data.message}`);
    } catch (error) {
      console.error('Upload error details:', error.response?.data || error.message);
      toast.error('Error uploading documents: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Process case
  const handleProcessCase = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/process-case/${caseId}`);
      setCaseDetails(response.data);
      setCurrentStep('processed');
      toast.success('Case processed successfully!');
    } catch (error) {
      toast.error('Error processing case: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Get baseline prediction
  const handlePredict = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/predict/${caseId}`);
      setPrediction(response.data);
      toast.success('Baseline prediction generated!');
    } catch (error) {
      toast.error('Error predicting: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Run simulation
  const handleSimulate = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/simulate/${caseId}?rounds=2`);
      setSimulation(response.data);
      setCurrentStep('simulated');
      toast.success('Simulation completed!');
    } catch (error) {
      toast.error('Error running simulation: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Find related laws for selected jurisdiction
  const handleFindLaws = async () => {
    if (!caseId) {
      toast.error('No case available');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get(`${API}/related-laws/${caseId}`, { params: { jurisdiction } });
      setRelatedLaws(response.data.laws || []);
      toast.success('Related laws fetched');
    } catch (error) {
      toast.error('Error fetching related laws: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Run audit
  const handleAudit = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/audit/${caseId}`);
      setAudit(response.data.audit_result);
      setCurrentStep('audited');
      toast.success('Bias audit completed!');
    } catch (error) {
      toast.error('Error auditing: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Generate PDF report for the case
  const handleGeneratePDF = async () => {
    if (!caseId) {
      toast.error('No case available');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get(`${API}/case-pdf/${caseId}`, {
        responseType: 'blob'
      });

      // response.data is a Blob (PDF). Use the response content-type if present.
      const contentType = response.headers['content-type'] || 'application/pdf';
      const blob = response.data instanceof Blob ? response.data : new Blob([response.data], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `case_${caseId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('PDF downloaded');
    } catch (error) {
      // When server returns an error JSON but responseType='blob', axios exposes a Blob
      // in error.response.data. Try to decode it to show the server message.
      try {
        if (error?.response?.data && error.response.data instanceof Blob) {
          const errText = await error.response.data.text();
          try {
            const errJson = JSON.parse(errText);
            toast.error('Error generating PDF: ' + (errJson.detail || errJson.message || JSON.stringify(errJson)));
          } catch (e) {
            toast.error('Error generating PDF: ' + errText);
          }
        } else {
          toast.error('Error generating PDF: ' + (error.response?.data?.detail || error.message));
        }
      } catch (inner) {
        console.error('Error handling PDF generation error:', inner, error);
        toast.error('Error generating PDF: ' + (error.message || 'Unknown error'));
      }
    } finally {
      setLoading(false);
    }
  };

  // Reset
  const handleReset = () => {
    setFiles([]);
    setCaseId(null);
    setRawText('');
    setCaseDetails(null);
    setPrediction(null);
    setSimulation(null);
    setAudit(null);
    setCurrentStep('upload');
  };

  return (
    <div className="App">
      {/* Header */}
      <header className="legal-header">
        <div className="header-content">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1 }}>
            <Scale size={48} color="#c9a961" />
            <div>
              <h1 className="header-title" data-testid="app-title">Legal Multi-Agent Courtroom</h1>
              <p className="header-subtitle" data-testid="app-subtitle">AI-Powered Case Analysis & Simulation System</p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ fontSize: '0.9rem', color: '#666' }}>
              Welcome, <strong>{user.name}</strong> ({user.roll_number})
            </span>
            <button
              onClick={handleLogout}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#dc2626',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: '600'
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="main-container">
        {/* Upload Section */}
        {currentStep === 'upload' && (
          <div className="section-card" data-testid="upload-section">
            <h2 className="section-title">
              <FileText size={32} />
              Upload Legal Documents
            </h2>
            <p className="section-subtitle">
              Upload multiple Indian legal case documents (PDF or TXT) and evidence files to begin the analysis. OCR will be automatically applied to scanned documents.
            </p>

            <div
              className={`upload-zone ${dragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input').click()}
              data-testid="upload-zone"
            >
              <Upload className="upload-icon" size={64} />
              <p className="upload-text">Drag and drop your documents here</p>
              <p className="upload-hint">or click to browse (supports multiple files: PDF or TXT)</p>
              <p style={{ fontSize: '0.85rem', color: '#999', marginTop: '0.5rem' }}>Scanned documents will be processed with OCR automatically</p>
              <input
                id="file-input"
                type="file"
                accept=".pdf,.txt"
                multiple
                onChange={handleFileChange}
                style={{ display: 'none' }}
                data-testid="file-input"
              />
            </div>

            <div style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <label style={{ fontWeight: 600 }}>Jurisdiction:</label>
              <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} className="select-jurisdiction">
                <option>India</option>
                <option>US</option>
                <option>Paris</option>
                <option>England</option>
                <option>Australia</option>
              </select>
            </div>

            {files && files.length > 0 && (
              <div className="file-list" data-testid="file-list" style={{ marginTop: '1rem', borderTop: '1px solid #e0e7ff', paddingTop: '1rem' }}>
                <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Selected Files ({files.length}):</p>
                <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                  {files.map((file, idx) => (
                    <div 
                      key={idx} 
                      className="file-info" 
                      data-testid={`file-info-${idx}`}
                      style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                    >
                      <span className="file-name">
                        <FileText size={18} style={{ display: 'inline', marginRight: '0.5rem' }} />
                        {file.name} ({(file.size / 1024).toFixed(2)} KB)
                      </span>
                      <button 
                        className="btn-remove" 
                        onClick={() => setFiles(files.filter((_, i) => i !== idx))} 
                        data-testid={`remove-file-btn-${idx}`}
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.85rem' }}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="action-buttons">
              <button
                className="btn-primary"
                onClick={handleUpload}
                disabled={files.length === 0 || loading}
                data-testid="upload-btn"
              >
                {loading ? <span className="loading-spinner"></span> : <Upload size={20} />}
                Upload Document
              </button>
            </div>
          </div>
        )}

        {/* Process Case Section */}
        {currentStep === 'process' && (
          <div className="section-card" data-testid="process-section">
            <h2 className="section-title">
              <FileText size={32} />
              Process Case Document
            </h2>
            <div className="status-badge success">
              <CheckCircle size={20} />
              Document uploaded successfully
            </div>

            <div className="case-preview">
              <p className="case-label">Raw Text Preview:</p>
              <p className="case-text">{rawText}</p>
            </div>

            <div className="action-buttons">
              <button
                className="btn-primary"
                onClick={handleProcessCase}
                disabled={loading}
                data-testid="process-btn"
              >
                {loading ? <span className="loading-spinner"></span> : <Play size={20} />}
                Extract Case Details
              </button>
              <button className="btn-secondary" onClick={handleReset} data-testid="reset-btn">
                Start Over
              </button>
            </div>
          </div>
        )}

        {/* Case Details Section */}
        {currentStep === 'processed' && caseDetails && (
          <div className="section-card" data-testid="case-details-section">
            <h2 className="section-title">
              <FileText size={32} />
              Case Analysis
            </h2>
            <div className="status-badge success">
              <CheckCircle size={20} />
              Case details extracted
            </div>

            <div className="case-preview">
              <div className="case-section">
                <p className="case-label">
                  <FileText size={20} />
                  Facts:
                </p>
                <p className="case-text">{caseDetails.facts}</p>
              </div>

              <div className="case-section">
                <p className="case-label">
                  <AlertCircle size={20} />
                  Issues:
                </p>
                <p className="case-text">{caseDetails.issues}</p>
              </div>

              <div className="case-section">
                <p className="case-label">
                  <Scale size={20} />
                  Holding:
                </p>
                <p className="case-text">{caseDetails.holding}</p>
              </div>
            </div>

            {prediction && (
              <div className="case-preview" style={{ marginTop: '1.5rem' }}>
                <p className="case-label">Baseline Classifier Prediction:</p>
                <div style={{ paddingLeft: '1.5rem' }}>
                  <p><strong>Prediction:</strong> {prediction.prediction}</p>
                  <p><strong>Confidence:</strong> {prediction.confidence}%</p>
                  <p><strong>Method:</strong> {prediction.method}</p>
                </div>
              </div>
            )}

            <div className="action-buttons">
              {!prediction && (
                <button
                  className="btn-secondary"
                  onClick={handlePredict}
                  disabled={loading}
                  data-testid="predict-btn"
                >
                  {loading ? <span className="loading-spinner"></span> : null}
                  Get Baseline Prediction
                </button>
              )}
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} className="select-jurisdiction">
                  <option>India</option>
                  <option>US</option>
                  <option>Paris</option>
                  <option>England</option>
                  <option>Australia</option>
                </select>

                <button
                  className="btn-secondary"
                  onClick={handleFindLaws}
                  disabled={loading || !caseId}
                  data-testid="find-laws-btn"
                >
                  {loading ? <span className="loading-spinner"></span> : null}
                  Find Relevant Laws
                </button>

                <button
                  className="btn-primary"
                  onClick={handleSimulate}
                  disabled={loading || !(relatedLaws && relatedLaws.length > 0)}
                  data-testid="simulate-btn"
                >
                  {loading ? <span className="loading-spinner"></span> : <Users size={20} />}
                  Run Multi-Agent Simulation
                </button>
              </div>
              <button className="btn-secondary" onClick={handleReset} data-testid="reset-btn-2">
                Start Over
              </button>
            </div>
          </div>
        )}

        {/* Related Laws preview (shown after fetching) */}
        {relatedLaws && relatedLaws.length > 0 && (
          <div className="section-card" data-testid="related-laws-section">
            <h2 className="section-title">
              <Scale size={32} />
              Relevant Laws & Citations
            </h2>
            <div className="case-preview">
              {relatedLaws.map((item, idx) => (
                <div key={idx} style={{ marginBottom: '0.75rem' }}>
                  <p style={{ fontWeight: 700 }}>{item.citation || `Law ${idx + 1}`}</p>
                  <p style={{ color: '#374151' }}>{item.summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Simulation Results Section */}
        {currentStep === 'simulated' && simulation && (
          <>
            <div className="section-card" data-testid="simulation-section">
              <h2 className="section-title">
                <Users size={32} />
                Court Simulation Transcript
              </h2>
              <div className="status-badge success">
                <CheckCircle size={20} />
                {simulation.rounds_completed} rounds completed
              </div>

              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="transcript">
                  <AccordionTrigger>View Debate Transcript</AccordionTrigger>
                  <AccordionContent>
                    {simulation.debate_transcript.map((item, index) => (
                      <div key={index} className="transcript-item" data-testid={`transcript-item-${index}`}>
                        <p className="round-indicator">Round {item.round}</p>
                        <span className={`speaker-badge ${item.speaker.toLowerCase().includes('plaintiff') ? 'plaintiff' : 'defendant'}`}>
                          {item.speaker}
                        </span>
                        <p className="argument-text">{item.argument}</p>
                      </div>
                    ))}
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </div>

            {/* Verdict Section */}
            <div className="verdict-card" data-testid="verdict-section">
              <h2 className="verdict-header">
                <Scale size={32} style={{ display: 'inline', marginRight: '0.75rem' }} />
                Judge's Verdict
              </h2>
              <div className="verdict-result" data-testid="verdict-result">
                {simulation.verdict.verdict}
              </div>
              <div>
                <p style={{ marginBottom: '0.5rem' }}>Confidence: {simulation.verdict.confidence}%</p>
                <div className="confidence-bar">
                  <div
                    className="confidence-fill"
                    style={{ width: `${simulation.verdict.confidence}%` }}
                    data-testid="confidence-bar"
                  ></div>
                </div>
              </div>

              {simulation.verdict.reasoning && (
                <div>
                  <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1.3rem' }}>Reasoning:</h3>
                  <ul className="reasoning-list">
                    {simulation.verdict.reasoning.map((reason, index) => (
                      <li key={index} className="reasoning-item" data-testid={`reasoning-${index}`}>
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {simulation.verdict.supporting_evidence && (
                <div>
                  <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1.3rem' }}>Supporting Evidence:</h3>
                  <ul className="reasoning-list">
                    {simulation.verdict.supporting_evidence.map((evidence, index) => (
                      <li key={index} className="reasoning-item" data-testid={`evidence-${index}`}>
                        {evidence}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="action-buttons">
              <button
                className="btn-primary"
                onClick={handleGeneratePDF}
                disabled={loading}
                data-testid="generate-pdf-btn"
              >
                {loading ? <span className="loading-spinner"></span> : <Scale size={20} />}
                Generate PDF Report
              </button>

              <button
                className="btn-primary"
                onClick={handleAudit}
                disabled={loading}
                data-testid="audit-btn"
              >
                {loading ? <span className="loading-spinner"></span> : <Shield size={20} />}
                Run Bias Audit
              </button>
              <button className="btn-secondary" onClick={handleReset} data-testid="reset-btn-3">
                Start New Case
              </button>
            </div>
          </>
        )}

        {/* Audit Results Section */}
        {currentStep === 'audited' && audit && (
          <div className="section-card" data-testid="audit-section">
            <h2 className="section-title">
              <Shield size={32} />
              Bias Audit Report
            </h2>

            <div className="bias-card">
              <div className="bias-score">
                <div className="score-circle">
                  <span className="score-value" data-testid="fairness-score">{audit.fairness_score}</span>
                </div>
                <p style={{ fontSize: '1.2rem', fontWeight: '600', color: '#1a2b4a' }}>Fairness Score (out of 100)</p>
              </div>

              {audit.biased_terms && audit.biased_terms.length > 0 && (
                <div>
                  <p style={{ fontWeight: '600', color: '#1a2b4a', marginBottom: '0.75rem' }}>Detected Biased Terms:</p>
                  <div className="bias-terms">
                    {audit.biased_terms.map((term, index) => (
                      <span key={index} className="bias-tag" data-testid={`bias-term-${index}`}>
                        {term}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {audit.bias_types && audit.bias_types.length > 0 && (
                <div style={{ marginTop: '1.5rem' }}>
                  <p style={{ fontWeight: '600', color: '#1a2b4a', marginBottom: '0.5rem' }}>Bias Categories:</p>
                  <p style={{ color: '#374151' }}>{audit.bias_types.join(', ')}</p>
                </div>
              )}

              {audit.recommendations && (
                <div style={{ marginTop: '1.5rem' }}>
                  <p style={{ fontWeight: '600', color: '#1a2b4a', marginBottom: '0.75rem' }}>Recommendations:</p>
                  <ul style={{ paddingLeft: '1.5rem', color: '#374151' }}>
                    {audit.recommendations.map((rec, index) => (
                      <li key={index} style={{ marginBottom: '0.5rem' }}>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {audit.summary && (
                <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'white', borderRadius: '8px' }}>
                  <p style={{ color: '#1a2b4a', fontWeight: '500' }}>{audit.summary}</p>
                </div>
              )}
            </div>

            <div className="action-buttons">
              <button className="btn-primary" onClick={handleReset} data-testid="new-case-btn">
                Analyze New Case
              </button>
              <button
                className="btn-primary"
                onClick={handleGeneratePDF}
                disabled={loading}
                style={{ marginLeft: '0.75rem' }}
                data-testid="generate-pdf-btn-2"
              >
                {loading ? <span className="loading-spinner"></span> : <Scale size={20} />}
                Generate PDF Report
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
