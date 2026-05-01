import { useState } from 'react';
import { X } from 'lucide-react';
import axios from 'axios';
import './CaseComparison.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function CaseComparison({ caseIds, onClose }) {
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    if (caseIds && caseIds.length >= 2) {
      loadComparison();
    }
  }, [caseIds]);

  const loadComparison = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/case-comparison`, {
        case_ids: caseIds
      });
      setComparison(response.data);
    } catch (error) {
      console.error('Error loading comparison:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!caseIds || caseIds.length < 2) {
    return null;
  }

  if (loading) {
    return (
      <div className="case-comparison">
        <div className="comparison-header">
          <h2>⚖️ Case Comparison</h2>
          <button className="close-btn" onClick={onClose}>
            <X size={24} />
          </button>
        </div>
        <div className="loading">Loading comparison data...</div>
      </div>
    );
  }

  if (!comparison) {
    return (
      <div className="case-comparison">
        <div className="comparison-header">
          <h2>⚖️ Case Comparison</h2>
          <button className="close-btn" onClick={onClose}>
            <X size={24} />
          </button>
        </div>
        <div className="error">Error loading comparison data</div>
      </div>
    );
  }

  const cases = comparison.cases || [];
  const similarities = comparison.similarities || [];
  const differences = comparison.differences || [];

  return (
    <div className="case-comparison">
      <div className="comparison-header">
        <h2>⚖️ Case Comparison</h2>
        <button className="close-btn" onClick={onClose}>
          <X size={24} />
        </button>
      </div>

      {/* Cases Grid */}
      <div className="comparison-grid">
        {cases.map((caseData, idx) => (
          <div key={idx} className="comparison-case">
            <div className="case-header">
              <h4>{caseData.case_id.slice(0, 12)}...</h4>
              <span className="jurisdiction-badge">{caseData.jurisdiction}</span>
            </div>

            <div className="case-sections">
              <div className="section">
                <h5>Facts</h5>
                <p className="section-content">{caseData.facts || 'No facts available'}</p>
              </div>

              <div className="section">
                <h5>Legal Issues</h5>
                <p className="section-content">{caseData.issues || 'No issues available'}</p>
              </div>

              <div className="section">
                <h5>Holding</h5>
                <p className="section-content">{caseData.holding || 'No holding available'}</p>
              </div>

              {caseData.prediction && (
                <div className="section">
                  <h5>Prediction</h5>
                  <div>
                    <p className="prediction-text">{caseData.prediction.prediction || 'N/A'}</p>
                    <div className="confidence-bar">
                      <div
                        className="confidence-fill"
                        style={{ width: `${caseData.prediction.confidence || 0}%` }}
                      ></div>
                    </div>
                    <p className="confidence-label">
                      {caseData.prediction.confidence?.toFixed(1) || 0}% confidence
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Similarities */}
      {similarities.length > 0 && (
        <div className="analysis-section similarities">
          <h4>🔗 Similarities</h4>
          <div className="tags-container">
            {similarities.map((sim, idx) => (
              <span key={idx} className="tag similarity-tag">
                {sim}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Differences */}
      {differences.length > 0 && (
        <div className="analysis-section differences">
          <h4>📊 Notable Differences</h4>
          {differences.map((diff, idx) => (
            <div key={idx} className="difference-item">
              <p className="diff-case">
                Case {diff.case_index + 1} Unique Aspects:
              </p>
              <div className="tags-container">
                {diff.aspects.map((aspect, aidx) => (
                  <span key={aidx} className="tag difference-tag">
                    {aspect}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Precedent Suggestion */}
      {cases.length > 1 && (
        <div className="analysis-section precedent">
          <h4>📜 Precedent Analysis</h4>
          <div className="precedent-info">
            <p>
              This comparison shows how similar cases with the same legal issues can have
              different outcomes based on factual distinctions and jurisdictional considerations.
            </p>
            {similarities.length > 0 && (
              <p className="highlight-text">
                The {similarities.length} common legal principle{similarities.length > 1 ? 's' : ''} across these cases
                could serve as binding or persuasive precedent.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
