import React, { useState, useEffect, useRef, useCallback } from 'react';
import { monitoringAPI, API_BASE_URL } from '../api/apiClient';
import BrowserCameraCapture from '../components/BrowserCameraCapture';
import '../styles/Monitoring.css';

const TOKEN_KEY = 'rsd_token';

const STATUS_COLORS = {
  monitoring: '#10b981',
  idle: '#6b7280',
  error: '#ef4444',
  offline: '#f59e0b',
};

const SEVERITY_COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#6b7280',
};

function StatusBadge({ status }) {
  return (
    <span className="status-badge" style={{ backgroundColor: STATUS_COLORS[status] || '#6b7280' }}>
      {status?.toUpperCase()}
    </span>
  );
}

function SeverityBadge({ severity }) {
  return (
    <span className="severity-badge" style={{ backgroundColor: SEVERITY_COLORS[severity] || '#6b7280' }}>
      {severity?.toUpperCase()}
    </span>
  );
}

export default function Monitoring() {
  const [cameras, setCameras] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [settings, setSettings] = useState(null);
  const [activeFeed, setActiveFeed] = useState(null);
  const [showRegister, setShowRegister] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [form, setForm] = useState({ camera_id: '', name: '', source: '', location: '' });
  const [settingsForm, setSettingsForm] = useState({});

  const wsRef = useRef(null);
  const pollRef = useRef(null);

  const token = localStorage.getItem(TOKEN_KEY);

  // ── Data loading ──────────────────────────────────────────────
  const loadCameras = useCallback(async () => {
    try {
      const res = await monitoringAPI.listCameras();
      setCameras(res.data.cameras || []);
    } catch (e) {
      setError('Failed to load cameras');
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      const res = await monitoringAPI.getAlerts(50, severityFilter !== 'all' ? severityFilter : undefined);
      setAlerts(res.data.alerts || []);
    } catch (e) { /* silent */ }
  }, [severityFilter]);

  const loadSettings = useCallback(async () => {
    try {
      const res = await monitoringAPI.getSettings();
      setSettings(res.data);
      setSettingsForm(res.data);
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => {
    loadCameras();
    loadAlerts();
    loadSettings();
  }, []);

  useEffect(() => {
    loadAlerts();
  }, [severityFilter]);

  // ── WebSocket ─────────────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    const wsBase = API_BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsBase}/monitoring/ws?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'alert') {
          setAlerts(prev => [msg.data, ...prev].slice(0, 100));
        } else if (msg.type === 'risk_assessment') {
          setCameras(prev => prev.map(c =>
            c.camera_id === msg.data.camera_id
              ? { ...c, last_risk_assessment: msg.data }
              : c
          ));
        } else if (msg.type === 'initial_state') {
          setCameras(msg.data.cameras || []);
          setAlerts(msg.data.alerts || []);
        }
      } catch { /* ignore parse errors */ }
    };

    // Poll camera status every 10s as a fallback
    pollRef.current = setInterval(loadCameras, 10000);

    return () => {
      ws.close();
      clearInterval(pollRef.current);
    };
  }, [token]);

  // ── Camera actions ────────────────────────────────────────────
  const registerCamera = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await monitoringAPI.registerCamera(form);
      setForm({ camera_id: '', name: '', source: '', location: '' });
      setShowRegister(false);
      await loadCameras();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to register camera');
    } finally {
      setLoading(false);
    }
  };

  const removeCamera = async (cameraId) => {
    if (!window.confirm(`Remove camera "${cameraId}"?`)) return;
    try {
      await monitoringAPI.removeCamera(cameraId);
      if (activeFeed === cameraId) setActiveFeed(null);
      await loadCameras();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to remove camera');
    }
  };

  const startMonitoring = async (cameraId) => {
    try {
      await monitoringAPI.startMonitoring(cameraId);
      await loadCameras();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start monitoring');
    }
  };

  const stopMonitoring = async (cameraId) => {
    try {
      await monitoringAPI.stopMonitoring(cameraId);
      if (activeFeed === cameraId) setActiveFeed(null);
      await loadCameras();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to stop monitoring');
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      await monitoringAPI.acknowledgeAlert(alertId);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, acknowledged: true } : a));
    } catch { /* silent */ }
  };

  const saveSettings = async (e) => {
    e.preventDefault();
    try {
      const res = await monitoringAPI.updateSettings(settingsForm);
      setSettings(res.data);
      setShowSettings(false);
    } catch (err) {
      setError('Failed to save settings');
    }
  };

  const feedUrl = (cameraId) =>
    `${API_BASE_URL}/monitoring/cameras/${cameraId}/feed?token=${token}`;

  const riskColor = (score) => {
    if (!score) return '#6b7280';
    if (score >= 80) return '#ef4444';
    if (score >= 60) return '#f97316';
    if (score >= 40) return '#f59e0b';
    return '#10b981';
  };

  const unacknowledged = alerts.filter(a => !a.acknowledged).length;

  return (
    <div className="monitoring-container">

      {/* Header */}
      <div className="monitoring-header">
        <div>
          <h2>🎥 Multi-Camera Monitoring</h2>
          <p className="subtitle">
            Real-time threat detection and risk assessment across all cameras
          </p>
        </div>
        <div className="monitoring-header-actions">
          <div className={`ws-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
            <span className="ws-dot" />
            {wsConnected ? 'Live' : 'Offline'}
          </div>
          <button className="btn-secondary" onClick={() => setShowSettings(!showSettings)}>
            ⚙️ Settings
          </button>
          <button className="btn-primary" onClick={() => setShowRegister(!showRegister)}>
            + Add Camera
          </button>
        </div>
      </div>

      {error && (
        <div className="monitoring-error" onClick={() => setError(null)}>
          ⚠️ {error} <span style={{ float: 'right', cursor: 'pointer' }}>✕</span>
        </div>
      )}

      {/* Register Camera Form */}
      {showRegister && (
        <div className="monitoring-card">
          <h3>Register New Camera</h3>
          <form onSubmit={registerCamera} className="register-form">
            <div className="form-row">
              <div className="form-field">
                <label>Camera ID *</label>
                <input
                  required
                  placeholder="e.g. CAM-01"
                  value={form.camera_id}
                  onChange={e => setForm({ ...form, camera_id: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label>Display Name *</label>
                <input
                  required
                  placeholder="e.g. Front Entrance"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-field">
                <label>Source *</label>
                <input
                  required
                  placeholder="RTSP URL or 0 for webcam"
                  value={form.source}
                  onChange={e => setForm({ ...form, source: e.target.value })}
                />
                <span className="field-hint">Use "browser" for your webcam, or an RTSP URL for an IP camera</span>
              </div>
              <div className="form-field">
                <label>Location</label>
                <input
                  placeholder="e.g. Building A, Floor 1"
                  value={form.location}
                  onChange={e => setForm({ ...form, location: e.target.value })}
                />
              </div>
            </div>
            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={() => setShowRegister(false)}>Cancel</button>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Registering…' : 'Register Camera'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Settings Panel */}
      {showSettings && settings && (
        <div className="monitoring-card">
          <h3>Monitoring Settings</h3>
          <form onSubmit={saveSettings} className="register-form">
            <div className="form-row">
              <div className="form-field">
                <label>Assessment Interval (seconds)</label>
                <input
                  type="number" min="60"
                  value={settingsForm.assessment_interval || ''}
                  onChange={e => setSettingsForm({ ...settingsForm, assessment_interval: parseInt(e.target.value) })}
                />
                <span className="field-hint">How often to compute risk scores (min 60s)</span>
              </div>
              <div className="form-field">
                <label>Frame Sample Interval (seconds)</label>
                <input
                  type="number" min="1"
                  value={settingsForm.frame_sample_interval || ''}
                  onChange={e => setSettingsForm({ ...settingsForm, frame_sample_interval: parseInt(e.target.value) })}
                />
              </div>
              <div className="form-field">
                <label>Risk Alert Threshold (0–100)</label>
                <input
                  type="number" min="0" max="100"
                  value={settingsForm.risk_threshold || ''}
                  onChange={e => setSettingsForm({ ...settingsForm, risk_threshold: parseFloat(e.target.value) })}
                />
                <span className="field-hint">Alert fires when risk score exceeds this</span>
              </div>
            </div>
            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={() => setShowSettings(false)}>Cancel</button>
              <button type="submit" className="btn-primary">Save Settings</button>
            </div>
          </form>
        </div>
      )}

      {/* Main Grid */}
      <div className="monitoring-grid">

        {/* Cameras */}
        <div className="cameras-section">
          <h3>Cameras ({cameras.length})</h3>

          {cameras.length === 0 ? (
            <div className="empty-state">
              <p>No cameras registered yet.</p>
              <button className="btn-primary" onClick={() => setShowRegister(true)}>+ Add your first camera</button>
            </div>
          ) : (
            <div className="cameras-grid">
              {cameras.map(cam => (
                <div key={cam.camera_id} className={`camera-card ${cam.status === 'monitoring' ? 'camera-card--active' : ''}`}>
                  <div className="camera-card-header">
                    <div>
                      <div className="camera-name">{cam.name}</div>
                      {cam.location && <div className="camera-location">📍 {cam.location}</div>}
                    </div>
                    <StatusBadge status={cam.status} />
                  </div>

                  {cam.last_risk_assessment && (
                    <div className="camera-risk">
                      <span style={{ color: riskColor(cam.last_risk_assessment.overall_score), fontWeight: 700, fontSize: '1.4rem' }}>
                        {cam.last_risk_assessment.overall_score?.toFixed(1)}
                      </span>
                      <span className="camera-risk-label">
                        Risk Score · {cam.last_risk_assessment.risk_level}
                      </span>
                    </div>
                  )}

                  {cam.error_message && (
                    <div className="camera-error-msg">⚠️ {cam.error_message}</div>
                  )}

                  {cam.last_frame_time && (
                    <div className="camera-last-frame">
                      Last frame: {new Date(cam.last_frame_time).toLocaleTimeString()}
                    </div>
                  )}

                  <div className="camera-card-actions">
                    {cam.status !== 'monitoring' ? (
                      <button className="btn-success btn-sm" onClick={() => startMonitoring(cam.camera_id)}>
                        ▶ Start
                      </button>
                    ) : (
                      <button className="btn-danger btn-sm" onClick={() => stopMonitoring(cam.camera_id)}>
                        ⏹ Stop
                      </button>
                    )}

                    {cam.status === 'monitoring' && cam.source !== 'browser' && (
                      <button
                        className={`btn-sm ${activeFeed === cam.camera_id ? 'btn-active' : 'btn-secondary'}`}
                        onClick={() => setActiveFeed(activeFeed === cam.camera_id ? null : cam.camera_id)}
                      >
                        {activeFeed === cam.camera_id ? '🔴 Hide Feed' : '📺 Live Feed'}
                      </button>
                    )}

                    <button className="btn-sm btn-remove" onClick={() => removeCamera(cam.camera_id)}>
                      🗑
                    </button>
                  </div>

                  {activeFeed === cam.camera_id && cam.source !== 'browser' && (
                    <div className="live-feed-wrapper">
                      <img
                        src={feedUrl(cam.camera_id)}
                        alt={`Live feed: ${cam.name}`}
                        className="live-feed"
                        onError={() => setError('Feed unavailable — camera may have stopped')}
                      />
                    </div>
                  )}

                  {cam.source === 'browser' && cam.status === 'monitoring' && (
                    <BrowserCameraCapture
                      cameraId={cam.camera_id}
                      cameraName={cam.name}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Alerts */}
        <div className="alerts-section">
          <div className="alerts-header">
            <h3>
              Alerts
              {unacknowledged > 0 && (
                <span className="alert-badge">{unacknowledged}</span>
              )}
            </h3>
            <div className="severity-filters">
              {['all', 'critical', 'high', 'medium', 'low'].map(s => (
                <button
                  key={s}
                  className={`filter-btn ${severityFilter === s ? 'filter-btn--active' : ''}`}
                  onClick={() => setSeverityFilter(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="alerts-list">
            {alerts.length === 0 ? (
              <div className="empty-state">
                <p>No alerts{severityFilter !== 'all' ? ` for severity: ${severityFilter}` : ''}.</p>
              </div>
            ) : (
              alerts.map(alert => (
                <div
                  key={alert.id}
                  className={`alert-item ${alert.acknowledged ? 'alert-item--ack' : ''}`}
                >
                  <div className="alert-item-top">
                    <SeverityBadge severity={alert.severity} />
                    <span className="alert-camera">{alert.camera_name}</span>
                    <span className="alert-time">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="alert-message">{alert.message}</div>
                  {!alert.acknowledged && (
                    <button
                      className="btn-sm btn-ack"
                      onClick={() => acknowledgeAlert(alert.id)}
                    >
                      ✓ Acknowledge
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
