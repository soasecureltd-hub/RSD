import React, { createContext, useContext, useReducer } from 'react';

const AssessmentContext = createContext(null);

const initialState = {
  assessment: null,
  anomalies: null,
  predictions: null,
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
      return { ...state, assessment: action.payload, anomalies: null, predictions: null, activeTab: 'results', error: null };
    case 'SET_ANOMALIES':
      return { ...state, anomalies: action.payload, activeTab: 'anomalies' };
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
