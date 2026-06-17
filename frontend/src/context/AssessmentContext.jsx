import React, { createContext, useContext, useReducer } from 'react';

const AssessmentContext = createContext(null);

const initialState = {
  assessment: null,
  anomalyResult: null,   // full object: {anomalies, multivariate_anomaly, anomaly_score, risk_velocity}
  predictions: null,     // full object including confidence
  loading: false,
  error: null,
  activeTab: 'input',
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_ASSESSMENT':
      return { ...state, assessment: action.payload, anomalyResult: null, predictions: null, activeTab: 'results', error: null };
    case 'SET_ANOMALY_RESULT':
      return { ...state, anomalyResult: action.payload };
    case 'SET_PREDICTIONS':
      return { ...state, predictions: action.payload };
    case 'SET_TAB':
      return { ...state, activeTab: action.payload };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function AssessmentProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AssessmentContext.Provider value={{ state, dispatch }}>
      {children}
    </AssessmentContext.Provider>
  );
}

export function useAssessment() {
  const ctx = useContext(AssessmentContext);
  if (!ctx) throw new Error('useAssessment must be used inside AssessmentProvider');
  return ctx;
}
