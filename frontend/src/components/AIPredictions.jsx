import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAssessment } from '../context/AssessmentContext';
import { riskAPI } from '../api/apiClient';
import '../styles/AIPredictions.css';

export default function AIPredictions({ assessmentId }) {
  const { state, dispatch } = useAssessment();
  const predictions = state.predictions;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [simulationMode, setSimulationMode] = useState(false);
  const [simPredictions, setSimPredictions] = useState(null);
  const [sliders, setSliders] = useState({ extra_guards: 0, improve_cctv: 0 });

  const displayPredictions = simulationMode ? simPredictions : predictions;

  const handleRunPredictions = async () => {
    if (!assessmentId) return;
    setLoading(true);
    setError(null);
    setSimulationMode(false);
    try {
      const response = await riskAPI.predict(assessmentId);
      dispatch({ type: 'SET_PREDICTIONS', payload: response.data });
    } catch (err) {
      setError(err.response?.data?.detail || 'Error running predictions');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulation = () => {
    if (!predictions) return;
    const improvementFactor = (sliders.extra_guards / 20 * 0.3) + (sliders.improve_cctv / 50 * 0.35);
    setSimPredictions({
      unauthorized_access: Math.max(0, predictions.unauthorized_access * (1 - improvementFactor)).toFixed(3),
      insider_threat: Math.max(0, predictions.insider_threat * (1 - improvementFactor * 0.7)).toFixed(3),
      emergency_failure: Math.max(0, predictions.emergency_failure * (1 - improvementFactor * 0.5)).toFixed(3),
      perimeter_breach: Math.max(0, predictions.perimeter_breach * (1 - improvementFactor)).toFixed(3),
    });
    setSimulationMode(true);
  };

  if (!assessmentId) {
    return (
      <div className="ai-predictions">
        <p style={{ textAlign: 'center', color: '#999' }}>👈 Please complete a risk assessment first</p>
      </div>
    );
  }

  const chartData = displayPredictions
    ? [
        { name: 'Unauthorized Access', prediction: (displayPredictions.unauthorized_access * 100).toFixed(1) },
        { name: 'Insider Threat', prediction: (displayPredictions.insider_threat * 100).toFixed(1) },
        { name: 'Emergency Failure', prediction: (displayPredictions.emergency_failure * 100).toFixed(1) },
        { name: 'Perimeter Breach', prediction: (displayPredictions.perimeter_breach * 100).toFixed(1) },
      ]
    : [];

  return (
    <div className="ai-predictions">
      <h2>🤖 AI Risk Predictions</h2>
      <p className="subtitle">
        Machine learning predictions powered by scikit-learn LogisticRegression
        {simulationMode && ' — showing What-If simulation'}
      </p>

      {error && <div className="error-message">{error}</div>}

      {!displayPredictions ? (
        <div className="predictions-cta">
          <button onClick={handleRunPredictions} disabled={loading} className="btn-primary">
            {loading ? 'Analyzing...' : '🚀 Run AI Predictions'}
          </button>
        </div>
      ) : (
        <>
          <div className="predictions-cards">
            {[
              { key: 'unauthorized_access', label: 'Unauthorized Access' },
              { key: 'insider_threat', label: 'Insider Threat' },
              { key: 'emergency_failure', label: 'Emergency Failure' },
              { key: 'perimeter_breach', label: 'Perimeter Breach' },
            ].map(({ key, label }) => (
              <div key={key} className="prediction-card">
                <h4>{label}</h4>
                <div className="risk-bar">
                  <div className="risk-fill" style={{ width: `${displayPredictions[key] * 100}%` }} />
                </div>
                <p className="percentage">{(displayPredictions[key] * 100).toFixed(1)}%</p>
              </div>
            ))}
          </div>

          <div className="chart-section">
            <h3>Prediction Overview</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                <YAxis label={{ value: 'Risk %', angle: -90, position: 'insideLeft' }} />
                <Tooltip formatter={(value) => `${value}%`} />
                <Bar dataKey="prediction" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="what-if-section">
            <h3>🔮 What-If Scenario Simulator</h3>
            <p>Adjust improvements and see projected risk reduction (simulation only)</p>
            <div className="slider-controls">
              <div className="slider-group">
                <label>Additional Security Guards: <strong>{sliders.extra_guards}</strong></label>
                <input
                  type="range" min="0" max="20" value={sliders.extra_guards}
                  onChange={(e) => setSliders({ ...sliders, extra_guards: parseInt(e.target.value) })}
                  className="slider"
                />
              </div>
              <div className="slider-group">
                <label>CCTV Improvement: <strong>{sliders.improve_cctv}%</strong></label>
                <input
                  type="range" min="0" max="50" value={sliders.improve_cctv}
                  onChange={(e) => setSliders({ ...sliders, improve_cctv: parseInt(e.target.value) })}
                  className="slider"
                />
              </div>
            </div>
            <button onClick={handleSimulation} className="btn-secondary">📊 Run Simulation</button>
            {simulationMode && (
              <div className="simulation-result">
                <p>
                  Simulation active.{' '}
                  <button className="btn-link" onClick={() => setSimulationMode(false)}>
                    Back to model predictions
                  </button>
                </p>
              </div>
            )}
          </div>

          <div className="action-buttons">
            <button onClick={handleRunPredictions} disabled={loading} className="btn-primary">
              🔄 Refresh Predictions
            </button>
          </div>
        </>
      )}
    </div>
  );
}
