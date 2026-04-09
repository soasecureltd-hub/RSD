import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import '../styles/AIPredictions.css';

export default function AIPredictions({ assessmentId, assessment }) {
  const [predictions, setPredictions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [simulationMode, setSimulationMode] = useState(false);
  const [sliders, setSliders] = useState({
    extra_guards: 0,
    improve_cctv: 0,
  });

  const riskLabels = [
    'Unauthorized Access',
    'Insider Threat',
    'Emergency Failure',
    'Perimeter Breach',
  ];

  // Mock predictions for demo (until ML model is integrated)
  const generateMockPredictions = () => {
    const mockPreds = {
      unauthorized_access: (Math.random() * 0.6).toFixed(3),
      insider_threat: (Math.random() * 0.4).toFixed(3),
      emergency_failure: (Math.random() * 0.5).toFixed(3),
      perimeter_breach: (Math.random() * 0.55).toFixed(3),
    };
    return mockPreds;
  };

  const handleRunPredictions = async () => {
    if (!assessmentId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // For now, use mock predictions since the ML model file may not exist
      const mockPreds = generateMockPredictions();
      setPredictions(mockPreds);
      setSimulationMode(false);
    } catch (err) {
      setError('Error running AI predictions: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulation = () => {
    if (!predictions) return;

    // Simulate risk reduction based on improvements
    const improvementFactor = (sliders.extra_guards + sliders.improve_cctv) / 100;
    
    const simulated = {
      unauthorized_access: Math.max(0, (predictions.unauthorized_access * (1 - improvementFactor * 0.3)).toFixed(3)),
      insider_threat: Math.max(0, (predictions.insider_threat * (1 - improvementFactor * 0.2)).toFixed(3)),
      emergency_failure: Math.max(0, (predictions.emergency_failure * (1 - improvementFactor * 0.25)).toFixed(3)),
      perimeter_breach: Math.max(0, (predictions.perimeter_breach * (1 - improvementFactor * 0.35)).toFixed(3)),
    };

    setPredictions(simulated);
    setSimulationMode(true);
  };

  if (!assessmentId) {
    return (
      <div className="ai-predictions">
        <p style={{ textAlign: 'center', color: '#999' }}>
          👈 Please complete a risk assessment first
        </p>
      </div>
    );
  }

  const chartData = predictions
    ? [
        { name: 'Unauthorized Access', prediction: (predictions.unauthorized_access * 100).toFixed(1) },
        { name: 'Insider Threat', prediction: (predictions.insider_threat * 100).toFixed(1) },
        { name: 'Emergency Failure', prediction: (predictions.emergency_failure * 100).toFixed(1) },
        { name: 'Perimeter Breach', prediction: (predictions.perimeter_breach * 100).toFixed(1) },
      ]
    : [];

  return (
    <div className="ai-predictions">
      <h2>🤖 AI Risk Predictions</h2>
      <p className="subtitle">Machine learning predictions for specific security risks</p>

      {error && <div className="error-message">{error}</div>}

      {!predictions ? (
        <div className="predictions-cta">
          <button onClick={handleRunPredictions} disabled={loading} className="btn-primary">
            {loading ? 'Analyzing...' : '🚀 Run AI Predictions'}
          </button>
        </div>
      ) : (
        <>
          <div className="predictions-cards">
            <div className="prediction-card">
              <h4>Unauthorized Access</h4>
              <div className="risk-bar">
                <div
                  className="risk-fill"
                  style={{ width: `${predictions.unauthorized_access * 100}%` }}
                />
              </div>
              <p className="percentage">{(predictions.unauthorized_access * 100).toFixed(1)}%</p>
            </div>

            <div className="prediction-card">
              <h4>Insider Threat</h4>
              <div className="risk-bar">
                <div
                  className="risk-fill"
                  style={{ width: `${predictions.insider_threat * 100}%` }}
                />
              </div>
              <p className="percentage">{(predictions.insider_threat * 100).toFixed(1)}%</p>
            </div>

            <div className="prediction-card">
              <h4>Emergency Failure</h4>
              <div className="risk-bar">
                <div
                  className="risk-fill"
                  style={{ width: `${predictions.emergency_failure * 100}%` }}
                />
              </div>
              <p className="percentage">{(predictions.emergency_failure * 100).toFixed(1)}%</p>
            </div>

            <div className="prediction-card">
              <h4>Perimeter Breach</h4>
              <div className="risk-bar">
                <div
                  className="risk-fill"
                  style={{ width: `${predictions.perimeter_breach * 100}%` }}
                />
              </div>
              <p className="percentage">{(predictions.perimeter_breach * 100).toFixed(1)}%</p>
            </div>
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
            <p>Adjust improvements and see how risk predictions change</p>

            <div className="slider-controls">
              <div className="slider-group">
                <label>
                  Additional Security Guards: <strong>{sliders.extra_guards}</strong>
                </label>
                <input
                  type="range"
                  min="0"
                  max="20"
                  value={sliders.extra_guards}
                  onChange={(e) => setSliders({ ...sliders, extra_guards: parseInt(e.target.value) })}
                  className="slider"
                />
              </div>

              <div className="slider-group">
                <label>
                  CCTV Improvement: <strong>{sliders.improve_cctv}%</strong>
                </label>
                <input
                  type="range"
                  min="0"
                  max="50"
                  value={sliders.improve_cctv}
                  onChange={(e) => setSliders({ ...sliders, improve_cctv: parseInt(e.target.value) })}
                  className="slider"
                />
              </div>
            </div>

            <button onClick={handleSimulation} className="btn-secondary">
              📊 Run Simulation
            </button>

            {simulationMode && (
              <div className="simulation-result">
                <p>✅ Simulation results shown above with projected improvements</p>
              </div>
            )}
          </div>

          <div className="action-buttons">
            <button onClick={handleRunPredictions} className="btn-primary">
              🔄 Refresh Predictions
            </button>
          </div>
        </>
      )}
    </div>
  );
}
