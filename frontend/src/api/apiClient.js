import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Risk assessment endpoints
export const riskAPI = {
  createAssessment: (data) => apiClient.post('/risk/assess', data),
  getAssessment: (id) => apiClient.get(`/risk/assess/${id}`),
  listAssessments: (skip = 0, limit = 100) => 
    apiClient.get(`/risk/assessments?skip=${skip}&limit=${limit}`),
  detectAnomalies: (assessmentId) => 
    apiClient.post(`/risk/anomaly/${assessmentId}`),
};

// Camera endpoints
export const cameraAPI = {
  analyzeFrame: (cameraId, frameData) => 
    apiClient.post('/camera/analyze', {
      camera_id: cameraId,
      frame_data: frameData,
    }),
  getCameraStatus: (cameraId = 'CAM-DEFAULT') => 
    apiClient.get(`/camera/health/${cameraId}`),
  getCameraHistory: (cameraId, limit = 100) => 
    apiClient.get(`/camera/history/${cameraId}?limit=${limit}`),
};

// Health check
export const health = () => apiClient.get('/');

export default apiClient;
