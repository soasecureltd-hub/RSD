import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { riskAPI, API_BASE_URL } from '../api/apiClient';
import '../styles/RiskResults.css';

const TOKEN_KEY = 'rsd_token';

const RISK_COLOR = (score) => {
  if (score <= 40) return '#28a745';
  if (score <= 60) return '#ffc107';
  if (score <= 80) return '#fd7e14';
  return '#dc3545';
};

const RISK_LABEL = (score) => {
  if (score <= 40) return 'LOW RISK';
  if (score <= 60) return 'MODERATE RISK';
  if (score <= 80) return 'HIGH RISK';
  return 'CRITICAL RISK';
};

const RECOMMENDATIONS = {
  'Physical Security':      'Improve perimeter integrity, upgrade lighting, and increase CCTV coverage.',
  'Access Control':         'Strengthen identity verification and restrict unauthorised area access.',
  'Personnel':              'Increase guard training frequency and ensure complete shift coverage.',
  'Incident History':       'Reduce incident frequency, improve response time, and maintain documentation.',
  'Emergency Preparedness': 'Conduct regular drills and upgrade communication and evacuation systems.',
};

function MiniGauge({ score }) {
  const color = RISK_COLOR(score);
  return (
    <div className="mini-gauge">
      <div className="mini-gauge-track">
        <div className="mini-gauge-fill" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="mini-gauge-label" style={{ color }}>{score.toFixed(1)}</span>
    </div>
  );
}

export default function RiskResults({ assessment, anomalyResult, predictions }) {
  if (!assessment) return null;

  const token = localStorage.getItem(TOKEN_KEY);

  const chartData = Object.entries(assessment.category_scores || {}).map(([name, value]) => ({
    name: name.replace(' ', '\n'),
    score: value,
    fill: RISK_COLOR(value),
  }));

  // Highest score = highest risk = biggest weakness (fix: sort descending)
  const sortedWeaknesses = Object.entries(assessment.category_scores || {})
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3);

  const handleDownloadReport = () => {
    if (!token) return;
    window.open(riskAPI.reportUrl(assessment.id, token), '_blank');
  };

  return (
    <div className="results-container">

      {/* Overall score */}
      <div className="overall-score" style={{ borderColor: RISK_COLOR(assessment.overall_score) }}>
        <div className="score-display">
          <h1 style={{ color: RISK_COLOR(assessment.overall_score) }}>
            {assessment.overall_score}/100
          </h1>
          <p className="risk-level" style={{ color: RISK_COLOR(assessment.overall_score) }}>
            {RISK_LABEL(assessment.overall_score)}
          </p>
          {assessment.facility_name && (
            <p className="facility-name">{assessment.facility_name}</p>
          )}
        </div>
      </div>

      {/* Inline AI + anomaly summary strip */}
      {(predictions || anomalyResult) && (
        <div className="insight-strip">
          {predictions && (
            <div className="insight-item">
              <span className="insight-label">Model Confidence</span>
              <span className="insight-value" style={{ color: RISK_COLOR(100 - predictions.confidence * 100) }}>
                {Math.round((predictions.confidence || 0) * 100)}%
              </span>
            </div>
          )}
          {anomalyResult && (
            <div className="insight-item">
              <span className="insight-label">Anomalies Found</span>
              <span className="insight-value" style={{ color: anomalyResult.total_anomalies > 0 ? '#ef4444' : '#10b981' }}>
                {anomalyResult.total_anomalies}
              </span>
            </div>
          )}
          {anomalyResult && (
            <div className="insight-item">
              <span className="insight-label">Anomaly Score</span>
              <span className="insight-value" style={{ color: RISK_COLOR(anomalyResult.anomaly_score * 100) }}>
                {(anomalyResult.anomaly_score * 100).toFixed(0)}/100
              </span>
            </div>
          )}
          {anomalyResult?.multivariate_anomaly && (
            <div className="insight-item insight-item--alert">
              <span className="insight-label">Global Pattern</span>
              <span className="insight-value">Anomalous</span>
            </div>
          )}
          {anomalyResult?.risk_velocity?.significant && (
            <div className={`insight-item ${anomalyResult.risk_velocity.direction === 'worsening' ? 'insight-item--alert' : 'insight-item--good'}`}>
              <span className="insight-label">Trend vs Last</span>
              <span className="insight-value">
                {anomalyResult.risk_velocity.direction === 'worsening' ? '▲' : '▼'}{' '}
                {Math.abs(anomalyResult.risk_velocity.overall_delta).toFixed(1)} pts
              </span>
            </div>
          )}
        </div>
      )}

      <div className="results-grid">
        <div className="chart-container">
          <h3>Category Scores</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} />
              <Tooltip formatter={(v) => [`${v}`, 'Score']} />
              <Bar dataKey="score" fill="#3b82f6" radius={[4, 4, 0, 0]}
                label={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="weaknesses-container">
          <h3>Top Risk Areas</h3>
          <div className="weakness-list">
            {sortedWeaknesses.map(([area, score], idx) => (
              <div key={area} className="weakness-item" style={{ borderLeftColor: RISK_COLOR(score) }}>
                <span className="weakness-rank" style={{ color: RISK_COLOR(score) }}>#{idx + 1}</span>
                <div className="weakness-info">
                  <p className="weakness-area">{area}</p>
                  <MiniGauge score={score} />
                  <p className="weakness-level" style={{ color: RISK_COLOR(score) }}>
                    {RISK_LABEL(score)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="recommendations-section">
        <h3>Priority Recommendations</h3>
        <div className="recommendations-list">
          {sortedWeaknesses.map(([area, score]) => (
            <div key={area} className="recommendation-item" style={{ borderLeftColor: RISK_COLOR(score) }}>
              <h4>{area}</h4>
              <p>{RECOMMENDATIONS[area]}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="action-buttons">
        <button onClick={handleDownloadReport} className="btn-primary" disabled={!token}>
          Download PDF Report
        </button>
      </div>
    </div>
  );
}
