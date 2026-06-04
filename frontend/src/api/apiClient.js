import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const TOKEN_KEY = 'rsd_token';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach token to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear token and dispatch logout event
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event('rsd:auth:logout'));
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => apiClient.post('/auth/register', data),
  loginJson: (data) => apiClient.post('/auth/login/json', data),
  getMe: () => apiClient.get('/auth/me'),
};

export const riskAPI = {
  createAssessment: (data) => apiClient.post('/risk/assess', data),
  getAssessment: (id) => apiClient.get(`/risk/assess/${id}`),
  listAssessments: (skip = 0, limit = 100) => apiClient.get(`/risk/assessments?skip=${skip}&limit=${limit}`),
  detectAnomalies: (assessmentId) => apiClient.post(`/risk/anomaly/${assessmentId}`),
  predict: (assessmentId) => apiClient.post(`/risk/predict/${assessmentId}`),
};

export const cameraAPI = {
  analyzeFrame: (cameraId, frameData, zones = []) => apiClient.post('/camera/analyze', { camera_id: cameraId, frame_data: frameData, zones }),
  getCameraStatus: (cameraId = 'CAM-DEFAULT') => apiClient.get(`/camera/health/${cameraId}`),
  getCameraHistory: (cameraId, limit = 100) => apiClient.get(`/camera/history/${cameraId}?limit=${limit}`),
  getCameraRiskEstimation: (cameraId = 'CAM-DEFAULT') => apiClient.get(`/camera/risk-estimation/${cameraId}`),
};

export const monitoringAPI = {
  listCameras: () => apiClient.get('/monitoring/cameras'),
  registerCamera: (data) => apiClient.post('/monitoring/cameras', data),
  removeCamera: (id) => apiClient.delete(`/monitoring/cameras/${id}`),
  getCamera: (id) => apiClient.get(`/monitoring/cameras/${id}`),
  startMonitoring: (id) => apiClient.post(`/monitoring/cameras/${id}/start`),
  stopMonitoring: (id) => apiClient.post(`/monitoring/cameras/${id}/stop`),
  getAlerts: (limit = 50, severity) =>
    apiClient.get('/monitoring/alerts', { params: { limit, ...(severity && { severity }) } }),
  acknowledgeAlert: (id) => apiClient.post(`/monitoring/alerts/${id}/acknowledge`),
  getSettings: () => apiClient.get('/monitoring/settings'),
  updateSettings: (data) => apiClient.put('/monitoring/settings', data),
};

export const health = () => apiClient.get('/');
export default apiClient;
