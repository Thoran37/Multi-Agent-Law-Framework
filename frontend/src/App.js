import { useState, useRef } from 'react';
import '@/App.css';
import axios from 'axios';
import { FileText, Scale, Users, Shield, Upload, Play, CheckCircle, LayoutDashboard, LogOut, GitCompare } from 'lucide-react';
import { toast } from 'sonner';
import Auth from '@/components/Auth';
import ProgressTracker from '@/components/ProgressTracker';
import DebateVisualization from '@/components/DebateVisualization';
import CaseDashboard from '@/components/CaseDashboard';
import CaseComparison from '@/components/CaseComparison';
import AnnotationSystem from '@/components/AnnotationSystem';
import Chatbot from '@/components/Chatbot';

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
  
  // UI State
  const [completedSteps, setCompletedSteps] = useState([]);
  const [processingTimes, setProcessingTimes] = useState({});
  const [showMenu, setShowMenu] = useState(false);
  const [currentView, setCurrentView] = useState('home'); // home, dashboard, case, comparison

  const trackStepCompletion = (stepName, startTime = null) => {
    if (startTime) {
      const duration = Date.now() - startTime;
      const seconds = (duration / 1000).toFixed(1);
      setProcessingTimes(prev => ({
        ...prev,
        [stepName]: `${seconds}s`
      }));
    }
    
    setCompletedSteps(prev => {
      if (!prev.includes(stepName)) {
        return [...prev, stepName];
      }
      return prev;
    });
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    setUser(null);
    handleReset();
    toast.success('Logged out successfully');
  };

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

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Please select at least one file');
      return;
    }

    setLoading(true);
    const startTime = Date.now();
    const formData = new FormData();
    
    files.forEach(file => {
      formData.append('files', file);
    });
    
    if (jurisdiction) formData.append('jurisdiction', jurisdiction);

    try {
      const response = await axios.post(`${API}/upload`, formData);
      setCaseId(response.data.case_id);
      setRawText(response.data.raw_text);
      setCurrentStep('process');
      trackStepCompletion('upload', startTime);
      toast.success(`${response.data.message}`);
    } catch (error) {
      console.error('Upload error details:', error.response?.data || error.message);
      toast.error('Error uploading documents: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleProcessCase = async () => {
    setLoading(true);
    const startTime = Date.now();
    try {
      const response = await axios.post(`${API}/process-case/${caseId}`);
      setCaseDetails(response.data);
      setCurrentStep('processed');
      trackStepCompletion('process', startTime);
      toast.success('Case processed successfully!');
    } catch (error) {
      toast.error('Error processing case: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handlePredict = async () => {
    setLoading(true);
    const startTime = Date.now();
    try {
      const response = await axios.post(`${API}/predict/${caseId}`);
      setPrediction(response.data);
      trackStepCompletion('predict', startTime);
      toast.success('Baseline prediction generated!');
    } catch (error) {
      toast.error('Error predicting: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    const startTime = Date.now();
    try {
      const response = await axios.post(`${API}/simulate/${caseId}?rounds=2`);
      setSimulation(response.data);
      setCurrentStep('simulated');
      trackStepCompletion('simulate', startTime);
      toast.success('Simulation completed!');
    } catch (error) {
      toast.error('Error running simulation: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

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

  const handleAudit = async () => {
    setLoading(true);
    const startTime = Date.now();
    try {
      const response = await axios.post(`${API}/audit/${caseId}`);
      setAudit(response.data.audit_result);
      setCurrentStep('audited');
      trackStepCompletion('audit', startTime);
      toast.success('Bias audit completed!');
    } catch (error) {
      toast.error('Error auditing: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

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

  const handleReset = () => {
    setFiles([]);
    setCaseId(null);
    setRawText('');
    setCaseDetails(null);
    setPrediction(null);
    setSimulation(null);
    setAudit(null);
    setCurrentStep('upload');
    setCompletedSteps([]);
    setProcessingTimes({});
    setCurrentView('home');
  };

  const handleSelectCaseFromDashboard = (caseId) => {
    setCaseId(caseId);
    setCurrentView('case');
    setCurrentStep('processed');
  };

  return (
    <div className="App">
      {/* Modern Navigation Header */}
      <header className="navbar">
        <div className="navbar-container">
          <div className="navbar-brand">
            <Scale size={32} className="navbar-logo" />
            <div className="brand-text">
              <h1>Legal AI Court</h1>
              <p>Multi-Agent Case Analysis System</p>
            </div>
          </div>

          {/* Navigation Menu */}
          <nav className="navbar-menu">
            <button
              className={`nav-item ${currentView === 'home' ? 'active' : ''}`}
              onClick={() => { setCurrentView('home'); setShowMenu(false); }}
            >
              <FileText size={18} />
              New Case
            </button>
            <button
              className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
              onClick={() => { setCurrentView('dashboard'); setShowMenu(false); }}
            >
              <LayoutDashboard size={18} />
              Dashboard
            </button>
            {caseId && (
              <button
                className={`nav-item ${currentView === 'comparison' ? 'active' : ''}`}
                onClick={() => { setCurrentView('comparison'); setShowMenu(false); }}
              >
                <GitCompare size={18} />
                Compare
              </button>
            )}
          </nav>

          {/* User Profile Dropdown */}
          <div className="navbar-user">
            <div className="user-menu-container">
              <button 
                className="user-avatar"
                onClick={() => setShowMenu(!showMenu)}
                title={user.name}
              >
                <span className="avatar-initials">
                  {user.name.split(' ').map(n => n[0]).join('').toUpperCase()}
                </span>
              </button>

              {showMenu && (
                <div className="dropdown-menu">
                  <div className="dropdown-header">
                    <p className="user-name">{user.name}</p>
                    <p className="user-id">{user.roll_number}</p>
                  </div>
                  <div className="dropdown-divider"></div>
                  <button className="dropdown-item" onClick={() => { setShowMenu(false); }}>
                    <FileText size={16} />
                    <span>Profile</span>
                  </button>
                  <button className="dropdown-item" onClick={() => { setShowMenu(false); }}>
                    <Shield size={16} />
                    <span>Settings</span>
                  </button>
                  <div className="dropdown-divider"></div>
                  <button 
                    className="dropdown-item logout"
                    onClick={() => {
                      setShowMenu(false);
                      handleLogout();
                    }}
                  >
                    <LogOut size={16} />
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Dashboard View */}
        {currentView === 'dashboard' && (
          <CaseDashboard onSelectCase={handleSelectCaseFromDashboard} />
        )}

        {/* Case Processing View */}
        {currentView === 'home' && (
          <div className="case-processing-container">
            {caseId && (
              <ProgressTracker 
                currentStep={currentStep}
                steps={{ upload: true, process: !!caseDetails, predict: !!prediction, simulate: !!simulation, audit: !!audit }}
                completedSteps={completedSteps}
                processingTimes={processingTimes}
              />
            )}

            {/* Upload Section */}
            {currentStep === 'upload' && (
              <div className="section-card upload-section">
                <div className="section-header">
                  <FileText size={32} className="section-icon" />
                  <div>
                    <h2>Upload Legal Documents</h2>
                    <p>Upload multiple case documents for analysis</p>
                  </div>
                </div>

                <div
                  className={`upload-zone ${dragging ? 'dragging' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('file-input').click()}
                >
                  <Upload className="upload-icon" size={64} />
                  <p className="upload-text">Drag documents here or click to browse</p>
                  <p className="upload-hint">PDF, Word (.docx, .doc), Images (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff), and TXT supported</p>
                  <input
                    id="file-input"
                    type="file"
                    accept=".pdf,.txt,.docx,.doc,.png,.jpg,.jpeg,.gif,.bmp,.webp,.tiff,.tif"
                    multiple
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                  />
                </div>

                {files.length > 0 && (
                  <div className="file-list">
                    <h4>Selected Files ({files.length})</h4>
                    <div className="files-grid">
                      {files.map((file, idx) => (
                        <div key={idx} className="file-item">
                          <FileText size={20} />
                          <span>{file.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="form-controls">
                  <div className="jurisdiction-select">
                    <label>Jurisdiction:</label>
                    <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)}>
                      <option>India</option>
                      <option>US</option>
                      <option>Paris</option>
                      <option>England</option>
                      <option>Australia</option>
                    </select>
                  </div>
                </div>

                <button
                  className="btn-primary"
                  onClick={handleUpload}
                  disabled={files.length === 0 || loading}
                >
                  <Upload size={20} />
                  {loading ? 'Uploading...' : 'Upload Documents'}
                </button>
              </div>
            )}

            {/* Process Case Section */}
            {currentStep === 'process' && (
              <div className="section-card">
                <div className="section-header">
                  <FileText size={32} className="section-icon" />
                  <div>
                    <h2>Process Case Document</h2>
                    <p>Extract structure and analyze legal content</p>
                  </div>
                </div>

                <div className="case-preview">
                  <h4>Document Preview</h4>
                  <div className="preview-text">{rawText}</div>
                </div>

                <div className="button-group">
                  <button className="btn-primary" onClick={handleProcessCase} disabled={loading}>
                    <Play size={20} />
                    {loading ? 'Processing...' : 'Extract Case Details'}
                  </button>
                  <button className="btn-secondary" onClick={handleReset}>
                    Start Over
                  </button>
                </div>
              </div>
            )}

            {/* Case Details Section */}
            {caseDetails && currentStep === 'processed' && (
              <div className="section-card">
                <div className="section-header">
                  <CheckCircle size={32} className="section-icon success" />
                  <div>
                    <h2>Case Details Extracted</h2>
                    <p>Review the extracted information</p>
                  </div>
                </div>

                <div className="case-details-grid">
                  <div className="detail-block">
                    <h4>Facts</h4>
                    <p>{caseDetails.facts}</p>
                  </div>
                  <div className="detail-block">
                    <h4>Issues</h4>
                    <p>{caseDetails.issues}</p>
                  </div>
                  <div className="detail-block">
                    <h4>Holding</h4>
                    <p>{caseDetails.holding}</p>
                  </div>
                </div>

                <div className="action-buttons">
                  <button className="btn-primary" onClick={handlePredict} disabled={loading}>
                    <Play size={20} />
                    {prediction ? 'Update Prediction' : 'Generate Prediction'}
                  </button>
                  <button className="btn-secondary" onClick={handleFindLaws} disabled={loading}>
                    <Shield size={20} />
                    Find Related Laws
                  </button>
                </div>

                {prediction && (
                  <div className="prediction-box">
                    <h4>Prediction Result</h4>
                    <p className="prediction-text">{prediction.prediction}</p>
                    <div className="confidence-bar">
                      <div style={{ width: `${prediction.confidence}%` }}></div>
                    </div>
                    <p className="confidence-text">{prediction.confidence}% confidence</p>
                  </div>
                )}

                {relatedLaws && (
                  <div className="laws-box">
                    <h4>Related Laws ({relatedLaws.length})</h4>
                    <div className="laws-list">
                      {relatedLaws.map((law, idx) => (
                        <div key={idx} className="law-item">
                          <p className="law-name">{law.citation || law}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Simulate Section */}
            {caseDetails && (
              <div className="section-card">
                <div className="section-header">
                  <Users size={32} className="section-icon" />
                  <div>
                    <h2>Court Simulation & Debate</h2>
                    <p>Run multi-agent debate simulation</p>
                  </div>
                </div>

                <button className="btn-primary" onClick={handleSimulate} disabled={loading}>
                  <Play size={20} />
                  {loading ? 'Running Simulation...' : 'Run Simulation'}
                </button>

                {simulation && (
                  <div>
                    <DebateVisualization simulation={simulation} />
                  </div>
                )}
              </div>
            )}

            {/* Audit Section */}
            {caseDetails && (
              <div className="section-card">
                <div className="section-header">
                  <Shield size={32} className="section-icon" />
                  <div>
                    <h2>Bias Audit</h2>
                    <p>Analyze for potential bias</p>
                  </div>
                </div>

                <button className="btn-primary" onClick={handleAudit} disabled={loading}>
                  <Shield size={20} />
                  {loading ? 'Running Audit...' : 'Run Audit Analysis'}
                </button>

                {audit && (
                  <div className="audit-results">
                    <h4>Audit Results</h4>
                    <div className="audit-json-wrapper">
                      <pre><code>{JSON.stringify(audit, null, 2)}</code></pre>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* PDF Export */}
            {simulation && (
              <div className="section-card">
                <div className="section-header">
                  <FileText size={32} className="section-icon" />
                  <div>
                    <h2>Export Report</h2>
                    <p>Generate and download complete case analysis as PDF</p>
                  </div>
                </div>

                <div className="pdf-export-wrapper">
                  <button className="btn-primary" onClick={handleGeneratePDF} disabled={loading}>
                    <FileText size={20} />
                    {loading ? 'Generating...' : 'Download PDF Report'}
                  </button>
                  <p className="export-description">
                    Download a comprehensive PDF report including case details, predictions, simulation results, and bias audit analysis.
                  </p>
                </div>
              </div>
            )}

            {/* Annotations */}
            {caseDetails && (
              <AnnotationSystem caseId={caseId} caseText={caseDetails.facts} />
            )}
          </div>
        )}

        {/* Case View */}
        {currentView === 'case' && caseId && (
          <div className="case-processing-container">
            {caseId && (
              <ProgressTracker 
                currentStep={currentStep}
                steps={{ upload: true, process: !!caseDetails, predict: !!prediction, simulate: !!simulation, audit: !!audit }}
                completedSteps={completedSteps}
                processingTimes={processingTimes}
              />
            )}
            {caseDetails && (
              <div className="section-card">
                <div className="case-details-grid">
                  <div className="detail-block">
                    <h4>Facts</h4>
                    <p>{caseDetails.facts}</p>
                  </div>
                  <div className="detail-block">
                    <h4>Issues</h4>
                    <p>{caseDetails.issues}</p>
                  </div>
                  <div className="detail-block">
                    <h4>Holding</h4>
                    <p>{caseDetails.holding}</p>
                  </div>
                </div>
              </div>
            )}

            {simulation && <DebateVisualization simulation={simulation} />}

            {caseDetails && (
              <AnnotationSystem caseId={caseId} caseText={caseDetails.facts} />
            )}
          </div>
        )}

        {/* Comparison View */}
        {currentView === 'comparison' && caseId && (
          <CaseComparison caseIds={[caseId]} onClose={() => setCurrentView('case')} />
        )}
      </main>

      {/* Chatbot - appears in bottom right, available after login */}
      <Chatbot 
        caseId={caseId}
        isActive={!!user}
        currentStep={currentStep}
        completedSteps={completedSteps}
        prediction={prediction}
        API={API}
      />
    </div>
  );
}

export default App;
