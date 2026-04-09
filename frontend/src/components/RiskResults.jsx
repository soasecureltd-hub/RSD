import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import '../styles/RiskResults.css';

const COLORS = {
  'Physical Security': '#3b82f6',
  'Access Control': '#ef4444',
  'Personnel': '#10b981',
  'Incident History': '#f59e0b',
  'Emergency Preparedness': '#8b5cf6',
};

const getRiskColor = (score) => {
  if (score <= 40) return '#28a745';
  if (score <= 60) return '#ffc107';
  if (score <= 80) return '#fd7e14';
  return '#dc3545';
};

const getRiskLabel = (score) => {
  if (score <= 40) return 'LOW RISK';
  if (score <= 60) return 'MODERATE RISK';
  if (score <= 80) return 'HIGH RISK';
  return 'CRITICAL RISK';
};

export default function RiskResults({ assessment, onAnomalyCheck }) {
  if (!assessment) return null;

  const chartData = Object.entries(assessment.category_scores || {}).map(([name, value]) => ({
    name,
    score: value,
  }));

  const recommendations = {
    'Physical Security': 'Improve perimeter integrity, upgrade lighting, increase CCTV coverage.',
    'Access Control': 'Strengthen identity verification and restricted area policies.',
    'Personnel': 'Increase guard training and ensure full shift coverage.',
    'Incident History': 'Reduce incident frequency, improve response time & documentation.',
    'Emergency Preparedness': 'Conduct regular drills and improve communication systems.',
  };

  const sortedWeaknesses = Object.entries(assessment.category_scores || {})
    .sort(([, a], [, b]) => a - b)
    .slice(0, 3);

  return (
    <div className="results-container">
      <div className="overall-score">
        <div className="score-display">
          <h1 style={{ color: getRiskColor(assessment.overall_score) }}>
            {assessment.overall_score}/100
          </h1>
          <p className="risk-level" style={{ color: getRiskColor(assessment.overall_score) }}>
            {getRiskLabel(assessment.overall_score)}
          </p>
        </div>
      </div>

      <div className="results-grid">
        <div className="chart-container">
          <h3>Category Scores</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Bar dataKey="score" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="weaknesses-container">
          <h3>Top Weaknesses</h3>
          <div className="weakness-list">
            {sortedWeaknesses.map(([area, score], idx) => (
              <div key={area} className="weakness-item">
                <span className="weakness-rank">#{idx + 1}</span>
                <div className="weakness-info">
                  <p className="weakness-area">{area}</p>
                  <p className="weakness-score">Score: {score}/100</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="recommendations-section">
        <h3>Priority Recommendations</h3>
        <div className="recommendations-list">
          {sortedWeaknesses.map(([area]) => (
            <div key={area} className="recommendation-item">
              <h4>{area}</h4>
              <p>{recommendations[area]}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="action-buttons">
        <button onClick={onAnomalyCheck} className="btn-secondary">
          🔍 Check for Anomalies
        </button>
      </div>
    </div>
  );
}
