import React, { useState } from 'react';
import RiskForm from '../components/RiskForm';
import RiskResults from '../components/RiskResults';
import AnomalyReport from '../components/AnomalyReport';
import AIPredictions from '../components/AIPredictions';
import { riskAPI } from '../api/apiClient';
import '../styles/Dashboard.css';

export default function Dashboard() {
  const [assessment, setAssessment] = useState(null);
  const [anomalies, setAnomalies] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('input');

  const handleAssessmentSubmit = async (formData) => {
    setLoading(true);
    setError(null);

    try {
      const response = await riskAPI.createAssessment(formData);
      setAssessment(response.data);
      setAnomalies(null);
      setActiveTab('results');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error creating assessment');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnomalyCheck = async () => {
    if (!assessment?.id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await riskAPI.detectAnomalies(assessment.id);
      setAnomalies(response.data.anomalies || []);
      setActiveTab('anomalies');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error detecting anomalies');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard">
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'input' ? 'active' : ''}`}
          onClick={() => setActiveTab('input')}
        >
          📝 Risk Assessment
        </button>
        {assessment && (
          <>
            <button
              className={`tab ${activeTab === 'results' ? 'active' : ''}`}
              onClick={() => setActiveTab('results')}
            >
              📊 Results
            </button>
            <button
              className={`tab ${activeTab === 'predictions' ? 'active' : ''}`}
              onClick={() => setActiveTab('predictions')}
            >
              🤖 AI Predictions
            </button>
            <button
              className={`tab ${activeTab === 'anomalies' ? 'active' : ''}`}
              onClick={() => setActiveTab('anomalies')}
            >
              🚨 Anomalies
            </button>
          </>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="tab-content">
        {activeTab === 'input' && (
          <RiskForm onSubmit={handleAssessmentSubmit} loading={loading} />
        )}

        {activeTab === 'results' && assessment && (
          <RiskResults assessment={assessment} onAnomalyCheck={handleAnomalyCheck} />
        )}

        {activeTab === 'predictions' && assessment && (
          <AIPredictions assessmentId={assessment?.id} assessment={assessment} />
        )}

        {activeTab === 'anomalies' && (
          <AnomalyReport anomalies={anomalies} />
        )}
      </div>
    </div>
  );
}
