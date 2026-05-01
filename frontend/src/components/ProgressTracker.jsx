import { CheckCircle, Clock, AlertCircle } from 'lucide-react';
import './ProgressTracker.css';

export default function ProgressTracker({ currentStep, steps, completedSteps, processingTimes }) {
  const stepConfig = {
    upload: { label: 'Upload', icon: '📄', color: '#3b82f6' },
    process: { label: 'Process', icon: '⚙️', color: '#8b5cf6' },
    predict: { label: 'Predict', icon: '🎯', color: '#ec4899' },
    simulate: { label: 'Debate', icon: '⚖️', color: '#f59e0b' },
    audit: { label: 'Audit', icon: '🔍', color: '#10b981' }
  };

  const getStepStatus = (step) => {
    if (completedSteps.includes(step)) return 'completed';
    if (steps[step]) return 'in-progress';
    return 'pending';
  };

  const getProgressPercentage = () => {
    return (completedSteps.length / Object.keys(steps).length) * 100;
  };

  return (
    <div className="progress-tracker">
      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div className="progress-bar-label">
          <h3>Case Processing Progress</h3>
          <span className="progress-percentage">{Math.round(getProgressPercentage())}%</span>
        </div>
        <div className="progress-bar">
          <div 
            className="progress-fill"
            style={{ width: `${getProgressPercentage()}%` }}
          ></div>
        </div>
      </div>

      {/* Step Indicators */}
      <div className="steps-container">
        {Object.keys(stepConfig).map((step, index) => {
          const status = getStepStatus(step);
          const config = stepConfig[step];
          
          return (
            <div key={step} className="step-wrapper">
              <div 
                className={`step-indicator ${status}`}
                style={{
                  borderColor: status === 'completed' || status === 'in-progress' ? config.color : '#e5e7eb',
                  backgroundColor: status === 'completed' ? config.color : status === 'in-progress' ? `${config.color}20` : '#f9fafb',
                }}
              >
                {status === 'completed' ? (
                  <CheckCircle size={24} color={config.color} />
                ) : (
                  <span className="step-icon">{config.icon}</span>
                )}
              </div>
              <p className={`step-label ${status}`}>{config.label}</p>
              
              {processingTimes[step] && (
                <div className="step-time">
                  <Clock size={14} />
                  {processingTimes[step]}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Timeline Events (recent steps) */}
      {completedSteps.length > 0 && (
        <div className="timeline-events">
          <h4>Completed Steps</h4>
          <div className="events-list">
            {completedSteps.map((step) => (
              <div key={step} className="event-item">
                <div className="event-dot"></div>
                <div className="event-content">
                  <p className="event-title">{stepConfig[step]?.label}</p>
                  <p className="event-time">{processingTimes[step] || 'Just now'}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
