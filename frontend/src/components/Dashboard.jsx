import { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  TrendingUp, 
  FileText, 
  Calendar, 
  MapPin, 
  Award,
  ChevronRight,
  BarChart3,
  Eye,
  Trash2
} from 'lucide-react';
import './Dashboard.css';

export default function Dashboard({ cases, onSelectCase, onCompare }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterJurisdiction, setFilterJurisdiction] = useState('All');
  const [filteredCases, setFilterCases] = useState(cases);
  const [selectedCaseIds, setSelectedCaseIds] = useState(new Set());

  useEffect(() => {
    let filtered = cases;

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(c => 
        c.case_id?.includes(searchTerm) ||
        c.facts?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.jurisdiction?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by jurisdiction
    if (filterJurisdiction !== 'All') {
      filtered = filtered.filter(c => c.jurisdiction === filterJurisdiction);
    }

    setFilterCases(filtered);
  }, [searchTerm, filterJurisdiction, cases]);

  const jurisdictions = ['All', ...new Set(cases.map(c => c.jurisdiction))];

  // Calculate statistics
  const stats = {
    totalCases: cases.length,
    averageConfidence: cases.length > 0 
      ? Math.round(cases.reduce((sum, c) => sum + (c.confidence || 0), 0) / cases.length)
      : 0,
    uniqueJurisdictions: new Set(cases.map(c => c.jurisdiction)).size,
    processedToday: cases.filter(c => {
      const caseDate = new Date(c.created_at).toDateString();
      const today = new Date().toDateString();
      return caseDate === today;
    }).length
  };

  const handleSelectCase = (caseId) => {
    const newSelected = new Set(selectedCaseIds);
    if (newSelected.has(caseId)) {
      newSelected.delete(caseId);
    } else {
      if (newSelected.size < 3) {
        newSelected.add(caseId);
      }
    }
    setSelectedCaseIds(newSelected);
  };

  const handleCompare = () => {
    if (selectedCaseIds.size < 2) {
      alert('Please select at least 2 cases to compare');
      return;
    }
    onCompare(Array.from(selectedCaseIds));
  };

  return (
    <div className="dashboard">
      {/* Stats Overview */}
      <div className="stats-overview">
        <h2 className="dashboard-title">📊 Case Dashboard</h2>
        <div className="stats-grid">
          <div className="stat-card primary">
            <div className="stat-icon">📋</div>
            <div className="stat-content">
              <p className="stat-label">Total Cases</p>
              <p className="stat-number">{stats.totalCases}</p>
            </div>
          </div>

          <div className="stat-card success">
            <div className="stat-icon">🎯</div>
            <div className="stat-content">
              <p className="stat-label">Avg Confidence</p>
              <p className="stat-number">{stats.averageConfidence}%</p>
            </div>
          </div>

          <div className="stat-card info">
            <div className="stat-icon">🏛️</div>
            <div className="stat-content">
              <p className="stat-label">Jurisdictions</p>
              <p className="stat-number">{stats.uniqueJurisdictions}</p>
            </div>
          </div>

          <div className="stat-card warning">
            <div className="stat-icon">📅</div>
            <div className="stat-content">
              <p className="stat-label">Today</p>
              <p className="stat-number">{stats.processedToday}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="search-filter-section">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search by case ID, facts, or jurisdiction..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="filter-box">
          <Filter size={20} />
          <select 
            value={filterJurisdiction}
            onChange={(e) => setFilterJurisdiction(e.target.value)}
            className="filter-select"
          >
            {jurisdictions.map(j => (
              <option key={j} value={j}>{j}</option>
            ))}
          </select>
        </div>

        {selectedCaseIds.size > 0 && (
          <button 
            className="btn-compare"
            onClick={handleCompare}
            disabled={selectedCaseIds.size < 2}
          >
            Compare {selectedCaseIds.size} Case{selectedCaseIds.size !== 1 ? 's' : ''}
          </button>
        )}
      </div>

      {/* Case History Table */}
      <div className="case-history">
        <h3 className="history-title">
          <FileText size={20} />
          Case History ({filteredCases.length})
        </h3>

        {filteredCases.length === 0 ? (
          <div className="no-cases">
            <FileText size={48} />
            <p>No cases found</p>
          </div>
        ) : (
          <div className="cases-table-container">
            <table className="cases-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input 
                      type="checkbox"
                      checked={selectedCaseIds.size === filteredCases.length && filteredCases.length > 0}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedCaseIds(new Set(filteredCases.map(c => c.case_id)));
                        } else {
                          setSelectedCaseIds(new Set());
                        }
                      }}
                    />
                  </th>
                  <th>Case ID</th>
                  <th>Jurisdiction</th>
                  <th>Date</th>
                  <th>Outcome</th>
                  <th>Confidence</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCases.map((caseItem) => (
                  <tr key={caseItem.case_id} className={selectedCaseIds.has(caseItem.case_id) ? 'selected' : ''}>
                    <td>
                      <input 
                        type="checkbox"
                        checked={selectedCaseIds.has(caseItem.case_id)}
                        onChange={() => handleSelectCase(caseItem.case_id)}
                      />
                    </td>
                    <td>
                      <span className="case-id-badge">{caseItem.case_id.slice(0, 8)}...</span>
                    </td>
                    <td>
                      <span className="jurisdiction-badge">{caseItem.jurisdiction}</span>
                    </td>
                    <td>
                      <span className="date-text">
                        {caseItem.created_at 
                          ? new Date(caseItem.created_at).toLocaleDateString()
                          : 'N/A'
                        }
                      </span>
                    </td>
                    <td>
                      <span className={`outcome-badge ${(caseItem.verdict || '').toLowerCase()}`}>
                        {caseItem.verdict || 'Pending'}
                      </span>
                    </td>
                    <td>
                      <div className="confidence-cell">
                        <span className="confidence-label">{caseItem.confidence || 0}%</span>
                        <div className="confidence-mini-bar">
                          <div 
                            className="confidence-mini-fill"
                            style={{ width: `${caseItem.confidence || 0}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <button 
                        className="action-btn view"
                        title="View details"
                        onClick={() => onSelectCase(caseItem.case_id)}
                      >
                        <Eye size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
