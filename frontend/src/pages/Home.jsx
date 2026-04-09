import React from 'react';
import '../styles/Home.css';

export default function Home({ onNavigate }) {
  return (
    <div className="home">
      <div className="hero">
        <h1>🔐 Risk-Security Diagnostic</h1>
        <p>Comprehensive facility security analysis and risk assessment</p>
      </div>

      <div className="features">
        <div className="feature-card">
          <h3>📝 Risk Assessment</h3>
          <p>Evaluate your facility's security posture across multiple dimensions</p>
        </div>
        <div className="feature-card">
          <h3>📊 Real-time Analytics</h3>
          <p>Get detailed scores, charts, and recommendations instantly</p>
        </div>
        <div className="feature-card">
          <h3>🎥 Camera Monitoring</h3>
          <p>Monitor camera health and video quality in real-time</p>
        </div>
        <div className="feature-card">
          <h3>🚨 Anomaly Detection</h3>
          <p>Identify unusual patterns and deviations from baseline metrics</p>
        </div>
      </div>

      <div className="cta">
        <button onClick={() => onNavigate('dashboard')} className="btn-primary-large">
          🚀 Start Assessment
        </button>
        <button onClick={() => onNavigate('camera')} className="btn-secondary-large">
          🎥 Monitor Camera
        </button>
      </div>
    </div>
  );
}
