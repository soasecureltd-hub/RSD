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
  createAssessment: (data) => apiClient.post('/api/risk/assess', data),
  getAssessment: (id) => apiClient.get(`/api/risk/assess/${id}`),
  listAssessments: (skip = 0, limit = 100) => 
    apiClient.get(`/api/risk/assessments?skip=${skip}&limit=${limit}`),
  detectAnomalies: (assessmentId) => 
    apiClient.post(`/api/risk/anomaly/${assessmentId}`),
};

// Camera endpoints
export const cameraAPI = {
  analyzeFrame: (cameraId, frameData) => 
    apiClient.post('/api/camera/analyze', {
      camera_id: cameraId,
      frame_data: frameData,
    }),
  getCameraStatus: (cameraId = 'CAM-DEFAULT') => 
    apiClient.get(`/api/camera/health/${cameraId}`),
  getCameraHistory: (cameraId, limit = 100) => 
    apiClient.get(`/api/camera/history/${cameraId}?limit=${limit}`),
};

// Health check
export const health = () => apiClient.get('/');

export default apiClient;
