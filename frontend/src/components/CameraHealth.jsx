import React, { useRef, useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { cameraAPI } from '../api/apiClient';
import '../styles/CameraHealth.css';

const CAPTURE_INTERVAL = 3000; // 3 seconds

export default function CameraHealth() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [recording, setRecording] = useState(false);
  const [health, setHealth] = useState(null);
  const [healthHistory, setHealthHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [cameraId] = useState('CAM-WEBCAM-001');
  const [lastCaptureTime, setLastCaptureTime] = useState(null);
  const intervalRef = useRef(null);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setRecording(true);
      setLastCaptureTime(new Date());
    } catch (err) {
      alert('Permission denied or camera not available: ' + err.message);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
    }
    setRecording(false);
    
    // Clear interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const captureAndAnalyze = async () => {
    if (!videoRef.current || !recording) return;

    try {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);

      // Convert to base64
      const frameData = canvas.toDataURL('image/jpeg').split(',')[1];

      // Send to backend
      const response = await cameraAPI.analyzeFrame(cameraId, frameData);
      
      // Update health data
      setHealth(response.data);
      setLastCaptureTime(new Date());

      // Add to history (keep last 20 readings)
      setHealthHistory(prev => {
        const updated = [
          ...prev,
          {
            timestamp: new Date().toLocaleTimeString(),
            score: response.data.health_score,
            blur: response.data.metrics.blur_score,
            brightness: response.data.metrics.brightness,
          }
        ];
        return updated.slice(-20); // Keep only last 20
      });
    } catch (err) {
      console.error('Error analyzing frame:', err);
    }
  };

  // Start auto-capture when recording
  useEffect(() => {
    if (recording && !intervalRef.current) {
      // Capture immediately
      captureAndAnalyze();

      // Then set interval for subsequent captures
      intervalRef.current = setInterval(() => {
        captureAndAnalyze();
      }, CAPTURE_INTERVAL);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [recording]);

  const getHealthColor = (score) => {
    if (score >= 80) return '#10b981'; // Green
    if (score >= 60) return '#f59e0b'; // Yellow
    if (score >= 40) return '#fd7e14'; // Orange
    return '#ef4444'; // Red
  };

  const getHealthLabel = (score) => {
    if (score >= 80) return '✅ EXCELLENT';
    if (score >= 60) return '⚠️ GOOD';
    if (score >= 40) return '🟠 FAIR';
    return '🔴 POOR';
  };

  const peopleCount = health?.object_counts?.person || 0;
  const objectCountEntries = health ? Object.entries(health.object_counts || {}) : [];

  return (
    <div className="camera-container">
      <h2>📹 Real-Time Camera Health Monitoring</h2>
      <p className="subtitle">Auto-captures every 3 seconds while recording</p>

      <div className="camera-section">
        <div className="video-wrapper">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            style={{
              width: '100%',
              maxWidth: '640px',
              backgroundColor: '#000',
              borderRadius: '8px',
            }}
          />
          <canvas
            ref={canvasRef}
            width={640}
            height={480}
            style={{ display: 'none' }}
          />
        </div>

        <div className="camera-controls">
          {!recording ? (
            <button onClick={startCamera} className="btn-primary">
              📷 Start Camera
            </button>
          ) : (
            <button onClick={stopCamera} className="btn-danger">
              ⏹️ Stop Camera
            </button>
          )}
        </div>

        {recording && (
          <div className="recording-indicator">
            <span className="pulse"></span>
            <span>🔴 LIVE - Capturing every 3 seconds</span>
          </div>
        )}
      </div>

      {health && (
        <>
          <div className="health-display">
            <div className="health-score-large">
              <div
                className="score-circle"
                style={{ borderColor: getHealthColor(health.health_score) }}
              >
                <div className="score-value">{health.health_score.toFixed(0)}</div>
                <div className="score-label">/100</div>
              </div>
              <div className="health-status" style={{ color: getHealthColor(health.health_score) }}>
                {getHealthLabel(health.health_score)}
              </div>
              {lastCaptureTime && (
                <div className="last-update">
                  Last update: {lastCaptureTime.toLocaleTimeString()}
                </div>
              )}
            </div>

            <div className="metrics-grid">
              <div className="metric-card">
                <h4>Blur Score</h4>
                <p className="value">{health.metrics.blur_score.toFixed(1)}</p>
                <p className="status">
                  {health.metrics.blur_score >= 100 ? '✅ Sharp' : '⚠️ Blurry'}
                </p>
              </div>

              <div className="metric-card">
                <h4>Brightness</h4>
                <p className="value">{health.metrics.brightness.toFixed(1)}</p>
                <p className="status">
                  {health.metrics.brightness >= 50 && health.metrics.brightness <= 200
                    ? '✅ Good'
                    : '⚠️ Poor'}
                </p>
              </div>

              <div className="metric-card">
                <h4>Contrast</h4>
                <p className="value">{health.metrics.contrast.toFixed(1)}</p>
                <p className="status">
                  {health.metrics.contrast >= 30 ? '✅ Good' : '⚠️ Low'}
                </p>
              </div>

              <div className="metric-card">
                <h4>Noise Level</h4>
                <p className="value">{health.metrics.noise_level.toFixed(1)}</p>
                <p className="status">
                  {health.metrics.noise_level < 50 ? '✅ Clean' : '⚠️ Noisy'}
                </p>
              </div>

              <div className="metric-card">
                <h4>FPS</h4>
                <p className="value">{health.metrics.fps.toFixed(1)}</p>
                <p className="status">
                  {health.metrics.fps >= 15 ? '✅ Good' : '⚠️ Low'}
                </p>
              </div>

              <div className="metric-card">
                <h4>Status</h4>
                <p className="value">{health.status === 'online' ? '🟢' : '🔴'}</p>
                <p className="status">{health.status.toUpperCase()}</p>
              </div>
            </div>
          </div>

          {health.detection_enabled !== undefined && (
            <div className="detection-summary">
              <h3>🔍 Object Detection</h3>
              {health.detection_enabled ? (
                <>
                  <div className="people-count-box">
                    <strong>{peopleCount}</strong>
                    <span>People Detected</span>
                  </div>

                  {objectCountEntries.length > 0 ? (
                    <div className="object-count-grid">
                      {objectCountEntries.map(([label, value]) => (
                        <div key={label} className="object-count-card">
                          <span className="object-label">{label}</span>
                          <span className="object-value">{value}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="no-objects">No visible objects detected in the current frame.</p>
                  )}

                  {health.detections && health.detections.length > 0 && (
                    <div className="detection-detail">
                      <h4>Detected Objects</h4>
                      <ul>
                        {health.detections.map((det, idx) => (
                          <li key={idx}>
                            <strong>{det.class}</strong> — {(det.confidence * 100).toFixed(1)}%
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <p className="detection-disabled">
                  Object detection is currently disabled or the YOLO model is not loaded.
                </p>
              )}
            </div>
          )}

          {health.issues && health.issues.length > 0 && (
            <div className="issues-alert">
              <h3>⚠️ Issues Detected</h3>
              <ul>
                {health.issues.map((issue, idx) => (
                  <li key={idx}>
                    {issue.replace(/_/g, ' ').toUpperCase()}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {healthHistory.length > 0 && (
            <div className="history-section">
              <h3>📈 Health Score Trend (Last 20 Readings)</h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={healthHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="timestamp" 
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#3b82f6"
                    dot={false}
                    name="Health Score"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>

              <div className="history-stats">
                <div className="stat">
                  <span>Average:</span>
                  <strong>
                    {(
                      healthHistory.reduce((sum, h) => sum + h.score, 0) / healthHistory.length
                    ).toFixed(1)}
                  </strong>
                </div>
                <div className="stat">
                  <span>Max:</span>
                  <strong>{Math.max(...healthHistory.map(h => h.score)).toFixed(1)}</strong>
                </div>
                <div className="stat">
                  <span>Min:</span>
                  <strong>{Math.min(...healthHistory.map(h => h.score)).toFixed(1)}</strong>
                </div>
                <div className="stat">
                  <span>Readings:</span>
                  <strong>{healthHistory.length}</strong>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

