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
  const { assessment, anomalyResult, predictions, loading, error, activeTab } = state;

  const handleAssessmentSubmit = async (formData) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });
    try {
      const response = await riskAPI.createAssessment(formData);
      const newAssessment = response.data;
      dispatch({ type: 'SET_ASSESSMENT', payload: newAssessment });

      // Auto-run anomaly detection and ML predictions in parallel
      const [anomalyRes, predRes] = await Promise.allSettled([
        riskAPI.detectAnomalies(newAssessment.id),
        riskAPI.predict(newAssessment.id),
      ]);

      if (anomalyRes.status === 'fulfilled') {
        dispatch({ type: 'SET_ANOMALY_RESULT', payload: anomalyRes.value.data });
      }
      if (predRes.status === 'fulfilled') {
        dispatch({ type: 'SET_PREDICTIONS', payload: predRes.value.data });
      }
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.response?.data?.detail || 'Error creating assessment' });
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
          Risk Assessment
        </button>
        {assessment && (
          <>
            <button
              className={`tab ${activeTab === 'results' ? 'active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TAB', payload: 'results' })}
            >
              Results
            </button>
            <button
              className={`tab ${activeTab === 'predictions' ? 'active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TAB', payload: 'predictions' })}
            >
              AI Predictions
              {predictions?.confidence != null && (
                <span className="tab-badge">{Math.round(predictions.confidence * 100)}%</span>
              )}
            </button>
            <button
              className={`tab ${activeTab === 'anomalies' ? 'active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TAB', payload: 'anomalies' })}
            >
              Anomalies
              {anomalyResult?.total_anomalies > 0 && (
                <span className="tab-badge tab-badge--danger">{anomalyResult.total_anomalies}</span>
              )}
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
          <RiskResults
            assessment={assessment}
            anomalyResult={anomalyResult}
            predictions={predictions}
          />
        )}
        {activeTab === 'predictions' && assessment && (
          <AIPredictions assessmentId={assessment.id} />
        )}
        {activeTab === 'anomalies' && (
          <AnomalyReport anomalyResult={anomalyResult} />
        )}
      </div>
    </div>
  );
}
