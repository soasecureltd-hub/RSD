import React, { useRef, useState, useEffect, useCallback } from 'react';
import { monitoringAPI } from '../api/apiClient';

const PUSH_INTERVAL = 3000; // send a frame every 3 seconds

export default function BrowserCameraCapture({ cameraId, cameraName }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const intervalRef = useRef(null);

  const [active, setActive] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);

  const startWebcam = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      setActive(true);
    } catch (e) {
      setError('Could not access webcam. Check browser permissions.');
    }
  };

  const stopWebcam = useCallback(() => {
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(t => t.stop());
      videoRef.current.srcObject = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setActive(false);
    setLastResult(null);
  }, []);

  const pushFrame = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return;

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const frameData = canvas.toDataURL('image/jpeg', 0.7).split(',')[1];

    try {
      const res = await monitoringAPI.pushFrame(cameraId, frameData);
      setLastResult(res.data);
    } catch (e) {
      if (e.response?.status === 400) {
        setError('Monitoring stopped on server — restart monitoring first.');
        stopWebcam();
      }
    }
  }, [cameraId, stopWebcam]);

  useEffect(() => {
    if (active) {
      pushFrame();
      intervalRef.current = setInterval(pushFrame, PUSH_INTERVAL);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [active, pushFrame]);

  // Stop webcam when component unmounts
  useEffect(() => () => stopWebcam(), [stopWebcam]);

  const healthColor = (score) => {
    if (!score) return '#6b7280';
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="browser-capture">
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {!active ? (
        <button className="btn-sm btn-primary" onClick={startWebcam}>
          📷 Enable Webcam
        </button>
      ) : (
        <button className="btn-sm btn-danger" onClick={stopWebcam}>
          ⏹ Stop Webcam
        </button>
      )}

      {error && <div className="browser-capture-error">{error}</div>}

      {active && (
        <div className="browser-capture-feed">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ width: '100%', borderRadius: '6px', display: 'block', background: '#000' }}
          />
          <div className="browser-capture-overlay">
            <span className="pulse" style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#ef4444', marginRight: 6 }} />
            LIVE · pushing every 3s
          </div>

          {lastResult && (
            <div className="browser-capture-stats">
              <span style={{ color: healthColor(lastResult.health_score), fontWeight: 700 }}>
                Health {lastResult.health_score?.toFixed(0)}/100
              </span>
              {Object.keys(lastResult.object_counts || {}).length > 0 && (
                <span>
                  {Object.entries(lastResult.object_counts)
                    .map(([k, v]) => `${v} ${k}`)
                    .join(' · ')}
                </span>
              )}
              {lastResult.zone_intrusions?.length > 0 && (
                <span style={{ color: '#ef4444', fontWeight: 700 }}>
                  🚨 {lastResult.zone_intrusions.length} intrusion{lastResult.zone_intrusions.length > 1 ? 's' : ''}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
