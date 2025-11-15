import { useState } from 'react';
import '@/App.css';
import axios from 'axios';
import { FileText, Scale, Users, Shield, Upload, Play, CheckCircle, AlertCircle } from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [file, setFile] = useState(null);
  const [caseId, setCaseId] = useState(null);
  const [rawText, setRawText] = useState('');
  const [caseDetails, setCaseDetails] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [simulation, setSimulation] = useState(null);
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState('upload');
  const [dragging, setDragging] = useState(false);

  // File upload handlers
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
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
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  // Upload document
  const handleUpload = async () => {
    if (!file) {
      toast.error('Please select a file first');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setCaseId(response.data.case_id);
      setRawText(response.data.raw_text);
      setCurrentStep('process');
      toast.success('Document uploaded successfully!');
    } catch (error) {
      toast.error('Error uploading document: ' + (error.response?.data?.detail || error.message));
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

  // Reset
  const handleReset = () => {
    setFile(null);
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <Scale size={48} color="#c9a961" />
            <div>
              <h1 className="header-title" data-testid="app-title">Legal Multi-Agent Courtroom</h1>
              <p className="header-subtitle" data-testid="app-subtitle">AI-Powered Case Analysis & Simulation System</p>
            </div>
          </div>
        </div>
      </header>

      <main className="main-container">
        {/* Upload Section */}
        {currentStep === 'upload' && (
          <div className="section-card" data-testid="upload-section">
            <h2 className="section-title">
              <FileText size={32} />
              Upload Legal Document
            </h2>
            <p className="section-subtitle">
              Upload an Indian legal case document in PDF or TXT format to begin the analysis.
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
              <p className="upload-text">Drag and drop your document here</p>
              <p className="upload-hint">or click to browse (PDF or TXT files)</p>
              <input
                id="file-input"
                type="file"
                accept=".pdf,.txt"
                onChange={handleFileChange}
                style={{ display: 'none' }}
                data-testid="file-input"
              />
            </div>

            {file && (
              <div className="file-info" data-testid="file-info">
                <span className="file-name">
                  <FileText size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
                  {file.name}
                </span>
                <button className="btn-remove" onClick={() => setFile(null)} data-testid="remove-file-btn">
                  Remove
                </button>
              </div>
            )}

            <div className="action-buttons">
              <button
                className="btn-primary"
                onClick={handleUpload}
                disabled={!file || loading}
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
              <button
                className="btn-primary"
                onClick={handleSimulate}
                disabled={loading}
                data-testid="simulate-btn"
              >
                {loading ? <span className="loading-spinner"></span> : <Users size={20} />}
                Run Multi-Agent Simulation
              </button>
              <button className="btn-secondary" onClick={handleReset} data-testid="reset-btn-2">
                Start Over
              </button>
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
                  <ul className="evidence-list">
                    {simulation.verdict.supporting_evidence.map((evidence, index) => (
                      <li key={index} className="evidence-item" data-testid={`evidence-${index}`}>
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
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
