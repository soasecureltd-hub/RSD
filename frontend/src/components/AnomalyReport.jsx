import React from 'react';
import '../styles/AnomalyReport.css';

export default function AnomalyReport({ anomalies }) {
  if (!anomalies || anomalies.length === 0) {
    return (
      <div className="anomaly-container">
        <h2>✅ No Anomalies Detected</h2>
        <p>All metrics are within normal ranges.</p>
      </div>
    );
  }

  const highSeverity = anomalies.filter(a => a.severity === 'HIGH');
  const mediumSeverity = anomalies.filter(a => a.severity === 'MEDIUM');

  return (
    <div className="anomaly-container">
      <h2>🚨 Anomaly Detection Report</h2>
      <p>{anomalies.length} anomalies detected</p>

      {highSeverity.length > 0 && (
        <div className="anomaly-section high">
          <h3>🔴 High Severity ({highSeverity.length})</h3>
          {highSeverity.map((anomaly, idx) => (
            <div key={idx} className="anomaly-item">
              <div className="anomaly-header">
                <span className="feature">{anomaly.feature}</span>
                <span className="zscore">Z-Score: {anomaly.z_score}</span>
              </div>
              <p className="message">{anomaly.message}</p>
              <p className="value">Current Value: {anomaly.value}</p>
            </div>
          ))}
        </div>
      )}

      {mediumSeverity.length > 0 && (
        <div className="anomaly-section medium">
          <h3>🟠 Medium Severity ({mediumSeverity.length})</h3>
          {mediumSeverity.map((anomaly, idx) => (
            <div key={idx} className="anomaly-item">
              <div className="anomaly-header">
                <span className="feature">{anomaly.feature}</span>
                <span className="zscore">Z-Score: {anomaly.z_score}</span>
              </div>
              <p className="message">{anomaly.message}</p>
              <p className="value">Current Value: {anomaly.value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
