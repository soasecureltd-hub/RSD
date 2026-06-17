import React from 'react';
import '../styles/AnomalyReport.css';

const FEATURE_LABELS = {
  incident_score:            'Incident Severity',
  unauthorized_access_score: 'Unauthorised Access',
  response_time_score:       'Response Time',
  cctv_uptime:               'CCTV Uptime',
  guard_adequacy:            'Guard Coverage',
  after_hours_security:      'After-Hours Security',
};

function AnomalyScoreBar({ score }) {
  const pct = Math.round(score * 100);
  const color = pct >= 70 ? '#ef4444' : pct >= 40 ? '#f97316' : '#10b981';
  return (
    <div className="anomaly-score-bar-wrap">
      <div className="anomaly-score-track">
        <div className="anomaly-score-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="anomaly-score-val" style={{ color }}>{pct}/100</span>
    </div>
  );
}

function VelocityPanel({ velocity }) {
  if (!velocity || !velocity.significant) return null;
  const worsening = velocity.direction === 'worsening';
  return (
    <div className={`velocity-panel ${worsening ? 'velocity-panel--bad' : 'velocity-panel--good'}`}>
      <div className="velocity-header">
        <span className="velocity-icon">{worsening ? '▲' : '▼'}</span>
        <strong>Risk Trend vs Previous Assessment</strong>
        <span className="velocity-delta" style={{ color: worsening ? '#ef4444' : '#10b981' }}>
          {worsening ? '+' : ''}{velocity.overall_delta.toFixed(1)} pts overall ({velocity.direction})
        </span>
      </div>
      {Object.keys(velocity.category_changes || {}).length > 0 && (
        <div className="velocity-categories">
          {Object.entries(velocity.category_changes).map(([cat, chg]) => (
            <div key={cat} className="velocity-cat-item">
              <span className="velocity-cat-name">{cat}</span>
              <span className="velocity-cat-arrow">{chg.direction === 'worsened' ? '▲' : '▼'}</span>
              <span className="velocity-cat-delta" style={{ color: chg.direction === 'worsened' ? '#ef4444' : '#10b981' }}>
                {chg.previous} → {chg.current} ({chg.delta > 0 ? '+' : ''}{chg.delta})
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AnomalyReport({ anomalyResult }) {
  if (!anomalyResult) {
    return (
      <div className="anomaly-container">
        <h2>Anomaly Detection</h2>
        <p style={{ color: '#9ca3af', textAlign: 'center', padding: '2rem' }}>
          Submit an assessment to run anomaly detection automatically.
        </p>
      </div>
    );
  }

  const { anomalies = [], multivariate_anomaly, anomaly_score, risk_velocity, total_anomalies } = anomalyResult;
  const highSeverity   = anomalies.filter(a => a.severity === 'HIGH');
  const mediumSeverity = anomalies.filter(a => a.severity === 'MEDIUM');

  return (
    <div className="anomaly-container">
      <h2>Anomaly Detection Report</h2>

      {/* Summary cards */}
      <div className="anomaly-summary-row">
        <div className="anomaly-summary-card">
          <span className="summary-label">Per-Feature Anomalies</span>
          <span className="summary-value" style={{ color: total_anomalies > 0 ? '#ef4444' : '#10b981' }}>
            {total_anomalies}
          </span>
        </div>
        <div className="anomaly-summary-card">
          <span className="summary-label">Anomaly Score</span>
          <AnomalyScoreBar score={anomaly_score || 0} />
        </div>
        <div className={`anomaly-summary-card ${multivariate_anomaly ? 'anomaly-summary-card--alert' : ''}`}>
          <span className="summary-label">Global Pattern</span>
          <span className="summary-value" style={{ color: multivariate_anomaly ? '#ef4444' : '#10b981', fontSize: '0.9rem' }}>
            {multivariate_anomaly ? 'Anomalous' : 'Normal'}
          </span>
          <span className="summary-sublabel">
            {multivariate_anomaly
              ? 'Multiple dimensions simultaneously abnormal'
              : 'Overall profile within expected range'}
          </span>
        </div>
      </div>

      {/* Risk velocity */}
      <VelocityPanel velocity={risk_velocity} />

      {total_anomalies === 0 && !multivariate_anomaly ? (
        <div className="anomaly-all-clear">
          <div className="all-clear-icon">✓</div>
          <h3>All Metrics Within Normal Range</h3>
          <p>No individual feature anomalies detected and the overall risk profile is normal.</p>
        </div>
      ) : (
        <>
          {multivariate_anomaly && total_anomalies === 0 && (
            <div className="anomaly-global-warning">
              <strong>Global Pattern Alert:</strong> No single feature is strongly anomalous, but the
              combination of your scores is unusual compared to typical facility profiles. Review
              the category breakdown for compounding risk factors.
            </div>
          )}

          {highSeverity.length > 0 && (
            <div className="anomaly-section high">
              <h3>High Severity ({highSeverity.length})</h3>
              {highSeverity.map((a, idx) => (
                <AnomalyCard key={idx} anomaly={a} />
              ))}
            </div>
          )}

          {mediumSeverity.length > 0 && (
            <div className="anomaly-section medium">
              <h3>Medium Severity ({mediumSeverity.length})</h3>
              {mediumSeverity.map((a, idx) => (
                <AnomalyCard key={idx} anomaly={a} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function AnomalyCard({ anomaly }) {
  const isAbove = anomaly.direction === 'above';
  return (
    <div className="anomaly-item">
      <div className="anomaly-header">
        <span className="feature">{FEATURE_LABELS[anomaly.feature] || anomaly.feature}</span>
        <div className="anomaly-meta">
          <span className="zscore">Z-Score: {anomaly.z_score > 0 ? '+' : ''}{anomaly.z_score}</span>
          {anomaly.direction && (
            <span className={`direction-badge direction-badge--${anomaly.direction}`}>
              {isAbove ? '▲ Above' : '▼ Below'} baseline
            </span>
          )}
        </div>
      </div>
      <p className="message">{anomaly.message}</p>
      <div className="anomaly-values">
        <span>Current: <strong>{anomaly.value}</strong></span>
        {anomaly.baseline_mean != null && (
          <span>Baseline avg: <strong>{anomaly.baseline_mean}</strong></span>
        )}
        {anomaly.percent_deviation != null && (
          <span>Deviation: <strong>{anomaly.percent_deviation}%</strong></span>
        )}
      </div>
    </div>
  );
}
