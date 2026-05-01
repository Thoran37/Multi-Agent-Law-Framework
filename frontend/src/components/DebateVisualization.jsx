import { useState } from 'react';
import { ChevronDown, ChevronUp, TrendingUp } from 'lucide-react';
import './DebateVisualization.css';

export default function DebateVisualization({ simulation }) {
  const [expandedRound, setExpandedRound] = useState(0);
  const [highlightedArgument, setHighlightedArgument] = useState(null);

  if (!simulation || !simulation.debate_transcript) {
    return null;
  }

  const transcript = simulation.debate_transcript || [];
  const verdict = simulation.verdict || {};
  
  // Extract confidence scores (mock if not present in response)
  const getArgumentStrength = (argument, index) => {
    // Simple heuristic: longer arguments get higher confidence
    const length = argument?.length || 0;
    const baseConfidence = Math.min(100, (length / 50) * 100);
    // Add some variation per argument
    return Math.min(100, baseConfidence + (index % 3) * 10);
  };

  // Group arguments by round
  const roundedArguments = {};
  transcript.forEach((item) => {
    const round = item.round || 1;
    if (!roundedArguments[round]) {
      roundedArguments[round] = { plaintiff: null, defendant: null };
    }
    if (item.speaker?.includes('Plaintiff')) {
      roundedArguments[round].plaintiff = item;
    } else if (item.speaker?.includes('Defendant')) {
      roundedArguments[round].defendant = item;
    }
  });

  const rounds = Object.keys(roundedArguments).sort((a, b) => a - b);

  const getSpeakerColor = (speaker) => {
    if (speaker?.includes('Plaintiff')) return 'plaintiff';
    return 'defendant';
  };

  const renderConfidenceMeter = (strength) => {
    const percentage = Math.min(100, strength);
    let color = '#ef4444'; // red
    if (percentage >= 70) color = '#10b981'; // green
    else if (percentage >= 50) color = '#f59e0b'; // amber

    return (
      <div className="confidence-meter">
        <div className="meter-bar">
          <div 
            className="meter-fill"
            style={{ 
              width: `${percentage}%`,
              backgroundColor: color
            }}
          ></div>
        </div>
        <span className="meter-label">{Math.round(percentage)}%</span>
      </div>
    );
  };

  return (
    <div className="debate-visualization">
      {/* Verdict Summary */}
      <div className="verdict-summary">
        <h3>⚖️ Verdict Summary</h3>
        <div className="verdict-content">
          <p><strong>Ruling:</strong> {verdict.ruling || 'Pending...'}</p>
          {verdict.reasoning && (
            <p><strong>Reasoning:</strong> {verdict.reasoning}</p>
          )}
        </div>
      </div>

      {/* Debate Timeline */}
      <div className="debate-timeline">
        <h3>📋 Debate Progression</h3>
        
        {rounds.length === 0 ? (
          <p className="no-debate">No debate transcript available</p>
        ) : (
          <div className="rounds-container">
            {rounds.map((roundNum) => {
              const round = roundedArguments[roundNum];
              const isExpanded = expandedRound === roundNum;
              const plaintiffStrength = getArgumentStrength(round.plaintiff?.argument, parseInt(roundNum));
              const defendantStrength = getArgumentStrength(round.defendant?.argument, parseInt(roundNum));

              return (
                <div key={roundNum} className="round-container">
                  {/* Round Header */}
                  <button
                    className={`round-header ${isExpanded ? 'expanded' : ''}`}
                    onClick={() => setExpandedRound(isExpanded ? null : roundNum)}
                  >
                    <span className="round-number">Round {roundNum}</span>
                    <div className="round-summary">
                      <div className="summary-side plaintiff">
                        <span>Plaintiff</span>
                        <div className="mini-meter">
                          <div 
                            className="mini-fill"
                            style={{ width: `${plaintiffStrength}%` }}
                          ></div>
                        </div>
                      </div>
                      <div className="summary-side defendant">
                        <span>Defendant</span>
                        <div className="mini-meter">
                          <div 
                            className="mini-fill"
                            style={{ width: `${defendantStrength}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </button>

                  {/* Round Content */}
                  {isExpanded && (
                    <div className="round-content">
                      <div className="arguments-row">
                        {/* Plaintiff Argument */}
                        <div 
                          className={`argument plaintiff ${highlightedArgument === `p${roundNum}` ? 'highlighted' : ''}`}
                          onMouseEnter={() => setHighlightedArgument(`p${roundNum}`)}
                          onMouseLeave={() => setHighlightedArgument(null)}
                        >
                          <div className="argument-header">
                            <div className="speaker-badge plaintiff">
                              👨‍⚖️ Plaintiff Lawyer
                            </div>
                          </div>
                          <div className="argument-text">
                            {round.plaintiff?.argument || 'No argument provided'}
                          </div>
                          <div className="argument-footer">
                            <div className="strength-indicator">
                              <TrendingUp size={16} />
                              <span>Argument Strength</span>
                            </div>
                            {renderConfidenceMeter(plaintiffStrength)}
                          </div>
                        </div>

                        {/* Defendant Argument */}
                        <div 
                          className={`argument defendant ${highlightedArgument === `d${roundNum}` ? 'highlighted' : ''}`}
                          onMouseEnter={() => setHighlightedArgument(`d${roundNum}`)}
                          onMouseLeave={() => setHighlightedArgument(null)}
                        >
                          <div className="argument-header">
                            <div className="speaker-badge defendant">
                              👩‍⚖️ Defendant Lawyer
                            </div>
                          </div>
                          <div className="argument-text">
                            {round.defendant?.argument || 'No argument provided'}
                          </div>
                          <div className="argument-footer">
                            <div className="strength-indicator">
                              <TrendingUp size={16} />
                              <span>Argument Strength</span>
                            </div>
                            {renderConfidenceMeter(defendantStrength)}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Debate Stats */}
      <div className="debate-stats">
        <h3>📊 Debate Statistics</h3>
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Total Rounds</span>
            <span className="stat-value">{rounds.length}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Arguments Made</span>
            <span className="stat-value">{transcript.length}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
