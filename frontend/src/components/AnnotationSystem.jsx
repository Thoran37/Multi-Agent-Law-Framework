import { useState, useEffect } from 'react';
import { Highlighter, MessageSquare, Pin, Tag } from 'lucide-react';
import axios from 'axios';
import './AnnotationSystem.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function AnnotationSystem({ caseId, caseText }) {
  const [annotations, setAnnotations] = useState([]);
  const [selectedText, setSelectedText] = useState('');
  const [annotationType, setAnnotationType] = useState('highlight');
  const [noteText, setNoteText] = useState('');
  const [showAnnotationForm, setShowAnnotationForm] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load annotations when component mounts
  useEffect(() => {
    if (caseId) {
      loadAnnotations();
    }
  }, [caseId]);

  const loadAnnotations = async () => {
    try {
      const response = await axios.get(`${API}/case/${caseId}/annotations`);
      setAnnotations(response.data.annotations || []);
    } catch (error) {
      console.error('Error loading annotations:', error);
    }
  };

  // Handle text selection
  const handleTextSelect = () => {
    const selection = window.getSelection().toString();
    if (selection) {
      setSelectedText(selection);
      setShowAnnotationForm(true);
    }
  };

  // Add annotation
  const handleAddAnnotation = async () => {
    if (!selectedText || !annotationType) {
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/case/${caseId}/annotations`, {
        text: selectedText,
        annotation: annotationType,
        note: noteText
      });

      // Reset form
      setSelectedText('');
      setNoteText('');
      setAnnotationType('highlight');
      setShowAnnotationForm(false);

      // Reload annotations
      await loadAnnotations();
    } catch (error) {
      console.error('Error adding annotation:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateSummary = () => {
    const highlights = annotations.filter(a => a.annotation === 'highlight');
    const pinnedItems = annotations.filter(a => a.annotation === 'pin');
    const notes = annotations.filter(a => a.note);

    return {
      totalAnnotations: annotations.length,
      highlights: highlights.length,
      pinnedItems: pinnedItems.length,
      notesCount: notes.length
    };
  };

  const summary = generateSummary();

  const getAnnotationIcon = (type) => {
    switch (type) {
      case 'highlight':
        return <Highlighter size={16} />;
      case 'pin':
        return <Pin size={16} />;
      case 'tag':
        return <Tag size={16} />;
      case 'comment':
        return <MessageSquare size={16} />;
      default:
        return <Tag size={16} />;
    }
  };

  const getAnnotationColor = (type) => {
    const colors = {
      highlight: '#fbbf24',
      pin: '#ef4444',
      tag: '#3b82f6',
      comment: '#8b5cf6'
    };
    return colors[type] || '#999';
  };

  return (
    <div className="annotation-system">
      {/* Summary Stats */}
      <div className="annotation-summary">
        <h4>📝 Evidence & Annotations</h4>
        <div className="summary-stats">
          <div className="summary-item">
            <span className="stat-label">Total</span>
            <span className="stat-value">{summary.totalAnnotations}</span>
          </div>
          <div className="summary-item">
            <span className="stat-label">Highlights</span>
            <span className="stat-value">{summary.highlights}</span>
          </div>
          <div className="summary-item">
            <span className="stat-label">Pinned</span>
            <span className="stat-value">{summary.pinnedItems}</span>
          </div>
          <div className="summary-item">
            <span className="stat-label">Notes</span>
            <span className="stat-value">{summary.notesCount}</span>
          </div>
        </div>
      </div>

      {/* Case Text with Annotation Support */}
      <div className="case-text-container">
        <p className="instruction">Select text to add annotations</p>
        <div
          className="case-text"
          onMouseUp={handleTextSelect}
        >
          {caseText || 'No case text available'}
        </div>
      </div>

      {/* Annotation Form */}
      {showAnnotationForm && (
        <div className="annotation-form">
          <div className="form-header">
            <h5>Add Annotation</h5>
            <button
              className="close-btn"
              onClick={() => {
                setShowAnnotationForm(false);
                setSelectedText('');
              }}
            >
              ✕
            </button>
          </div>

          <div className="selected-text-preview">
            <strong>Selected:</strong>
            <p>{selectedText.substring(0, 100)}...</p>
          </div>

          <div className="form-group">
            <label>Type</label>
            <div className="type-options">
              {['highlight', 'pin', 'tag', 'comment'].map(type => (
                <button
                  key={type}
                  className={`type-btn ${annotationType === type ? 'active' : ''}`}
                  onClick={() => setAnnotationType(type)}
                  style={{
                    borderColor: annotationType === type ? getAnnotationColor(type) : '#ddd'
                  }}
                >
                  {getAnnotationIcon(type)}
                  <span>{type.charAt(0).toUpperCase() + type.slice(1)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="note">Note (optional)</label>
            <textarea
              id="note"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Add a note about this annotation"
              rows="3"
            />
          </div>

          <div className="form-actions">
            <button
              className="btn-add"
              onClick={handleAddAnnotation}
              disabled={loading}
            >
              {loading ? 'Adding...' : 'Add Annotation'}
            </button>
            <button
              className="btn-cancel"
              onClick={() => {
                setShowAnnotationForm(false);
                setSelectedText('');
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Annotations List */}
      <div className="annotations-list">
        <h4>All Annotations ({annotations.length})</h4>
        {annotations.length === 0 ? (
          <p className="no-annotations">
            No annotations yet. Select text in the case to start annotating.
          </p>
        ) : (
          <div className="annotations">
            {annotations.map((ann, idx) => (
              <div
                key={idx}
                className="annotation-item"
                style={{ borderLeftColor: getAnnotationColor(ann.annotation) }}
              >
                <div className="annotation-header">
                  <div className="annotation-type">
                    {getAnnotationIcon(ann.annotation)}
                    <span>{ann.annotation}</span>
                  </div>
                  <div className="annotation-time">
                    {new Date(ann.timestamp).toLocaleDateString()}
                  </div>
                </div>

                <p className="annotation-text">"{ann.text}"</p>

                {ann.note && (
                  <div className="annotation-note">
                    <strong>Note:</strong> {ann.note}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Generate Summary Button */}
      {annotations.length > 0 && (
        <div className="summary-generation">
          <button className="btn-generate-summary">
            📄 Generate Summary from Annotations
          </button>
        </div>
      )}
    </div>
  );
}
