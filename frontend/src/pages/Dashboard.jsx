import React from 'react';
import RiskForm from '../components/RiskForm';
import RiskResults from '../components/RiskResults';
import AnomalyReport from '../components/AnomalyReport';
import AIPredictions from '../components/AIPredictions';
import { useAssessment } from '../context/AssessmentContext';
import { riskAPI } from '../api/apiClient';
import '../styles/Dashboard.css';

export default function Dashboard() {
  const { state, dispatch } = useAssessment();
  const { assessment, anomalies, loading, error, activeTab } = state;

  const handleAssessmentSubmit = async (formData) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });
    try {
      const response = await riskAPI.createAssessment(formData);
      dispatch({ type: 'SET_ASSESSMENT', payload: response.data });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.response?.data?.detail || 'Error creating assessment' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const handleAnomalyCheck = async () => {
    if (!assessment?.id) return;
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });
    try {
      const response = await riskAPI.detectAnomalies(assessment.id);
      dispatch({ type: 'SET_ANOMALIES', payload: response.data.anomalies || [] });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.response?.data?.detail || 'Error detecting anomalies' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  return (
    <div className="dashboard">
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'input' ? 'active' : ''}`}
          onClick={() => dispatch({ type: 'SET_TAB', payload: 'input' })}
        >
          📝 Risk Assessment
        </button>
        {assessment && (
          <>
            <button
              className={`tab ${activeTab === 'results' ? 'active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TAB', payload: 'results' })}
            >
              📊 Results
            </button>
            <button
              className={`tab ${activeTab === 'predictions' ? 'active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TAB', payload: 'predictions' })}
            >
              🤖 AI Predictions
            </button>
            <button
              className={`tab ${activeTab === 'anomalies' ? 'active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TAB', payload: 'anomalies' })}
            >
              🚨 Anomalies
            </button>
          </>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="tab-content">
        {activeTab === 'input' && <RiskForm onSubmit={handleAssessmentSubmit} loading={loading} />}
        {activeTab === 'results' && assessment && <RiskResults assessment={assessment} onAnomalyCheck={handleAnomalyCheck} />}
        {activeTab === 'predictions' && assessment && <AIPredictions assessmentId={assessment.id} assessment={assessment} />}
        {activeTab === 'anomalies' && <AnomalyReport anomalies={anomalies} />}
      </div>
    </div>
  );
}
