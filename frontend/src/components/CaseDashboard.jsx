import { useState, useEffect } from 'react';
import { Search, Filter, TrendingUp, FileText, BarChart3, Clock } from 'lucide-react';
import axios from 'axios';
import './CaseDashboard.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function CaseDashboard({ onSelectCase }) {
  const [cases, setCases] = useState([]);
  const [stats, setStats] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterJurisdiction, setFilterJurisdiction] = useState('');
  const [filteredCases, setFilteredCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState('date');

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/cases`);
      setCases(response.data.cases);
      setStats(response.data.stats);
      setFilteredCases(response.data.cases);
    } catch (error) {
      console.error('Error fetching cases:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleFilter();
  }, [searchQuery, filterJurisdiction, cases, sortBy]);

  const handleFilter = () => {
    let filtered = [...cases];

    // Filter by search query
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(c =>
        c.facts?.toLowerCase().includes(q) ||
        c.issues?.toLowerCase().includes(q) ||
        c.holding?.toLowerCase().includes(q) ||
        c.jurisdiction?.toLowerCase().includes(q)
      );
    }

    // Filter by jurisdiction
    if (filterJurisdiction) {
      filtered = filtered.filter(c => c.jurisdiction === filterJurisdiction);
    }

    // Sort
    filtered.sort((a, b) => {
      if (sortBy === 'date') {
        return new Date(b.upload_timestamp) - new Date(a.upload_timestamp);
      } else if (sortBy === 'confidence') {
        return (b.prediction_confidence || 0) - (a.prediction_confidence || 0);
      }
      return 0;
    });

    setFilteredCases(filtered);
  };

  const jurisdictions = stats?.jurisdiction_breakdown ? Object.keys(stats.jurisdiction_breakdown) : [];

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Unknown';
    return new Date(timestamp).toLocaleDateString();
  };

  return (
    <div className="case-dashboard">
      {/* Stats Cards */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card primary">
            <div className="stat-icon">📊</div>
            <div className="stat-info">
              <p className="stat-label">Total Cases</p>
              <p className="stat-value">{stats.total_cases}</p>
            </div>
          </div>

          <div className="stat-card success">
            <div className="stat-icon">⚖️</div>
            <div className="stat-info">
              <p className="stat-label">Avg Confidence</p>
              <p className="stat-value">{stats.avg_confidence.toFixed(1)}%</p>
            </div>
          </div>

          <div className="stat-card info">
            <div className="stat-icon">⚡</div>
            <div className="stat-info">
              <p className="stat-label">Simulations Run</p>
              <p className="stat-value">{stats.cases_with_simulation}</p>
            </div>
          </div>

          <div className="stat-card warning">
            <div className="stat-icon">🔍</div>
            <div className="stat-info">
              <p className="stat-label">Audits Completed</p>
              <p className="stat-value">{stats.cases_with_audit}</p>
            </div>
          </div>
        </div>
      )}

      {/* Search and Filter */}
      <div className="dashboard-controls">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search cases by facts, issues, or jurisdiction..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-controls">
          <select
            value={filterJurisdiction}
            onChange={(e) => setFilterJurisdiction(e.target.value)}
            className="filter-select"
          >
            <option value="">All Jurisdictions</option>
            {jurisdictions.map(jur => (
              <option key={jur} value={jur}>{jur}</option>
            ))}
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="filter-select"
          >
            <option value="date">Latest First</option>
            <option value="confidence">Highest Confidence</option>
          </select>
        </div>
      </div>

      {/* Cases List */}
      <div className="cases-container">
        <h3 className="cases-header">
          {filteredCases.length} Case{filteredCases.length !== 1 ? 's' : ''} Found
        </h3>

        {loading ? (
          <div className="loading">Loading cases...</div>
        ) : filteredCases.length === 0 ? (
          <div className="no-cases">No cases found. Upload a new case to get started.</div>
        ) : (
          <div className="cases-list">
            {filteredCases.map(caseItem => (
              <div
                key={caseItem.case_id}
                className="case-card"
                onClick={() => onSelectCase(caseItem.case_id)}
              >
                <div className="case-header">
                  <div className="case-title">
                    <FileText size={18} />
                    <span className="case-id">{caseItem.case_id.slice(0, 8)}...</span>
                  </div>
                  <span className="case-jurisdiction">{caseItem.jurisdiction}</span>
                </div>

                <div className="case-content">
                  <div className="case-meta">
                    <Clock size={14} />
                    <span>{formatDate(caseItem.upload_timestamp)}</span>
                  </div>

                  <p className="case-issues">
                    <strong>Issues:</strong> {caseItem.issues?.slice(0, 100)}...
                  </p>

                  {caseItem.prediction_confidence !== undefined && (
                    <div className="case-confidence">
                      <span>Confidence: {caseItem.prediction_confidence?.toFixed(1) || 0}%</span>
                      <div className="confidence-bar">
                        <div
                          className="confidence-fill"
                          style={{ width: `${caseItem.prediction_confidence || 0}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="case-status-badges">
                  {caseItem.has_prediction && <span className="badge prediction">✓ Predicted</span>}
                  {caseItem.has_simulation && <span className="badge simulation">✓ Simulated</span>}
                  {caseItem.has_audit && <span className="badge audit">✓ Audited</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
