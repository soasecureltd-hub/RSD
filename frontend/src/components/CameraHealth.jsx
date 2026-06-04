import React, { useRef, useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { cameraAPI } from '../api/apiClient';
import '../styles/CameraHealth.css';

const CAPTURE_INTERVAL = 3000; // 3 seconds

export default function CameraHealth() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const svgRef = useRef(null);
  
  const [recording, setRecording] = useState(false);
  const [health, setHealth] = useState(null);
  const [healthHistory, setHealthHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [cameraId] = useState('CAM-WEBCAM-001');
  const [lastCaptureTime, setLastCaptureTime] = useState(null);
  const intervalRef = useRef(null);

  // Vision Zone States
  const [zones, setZones] = useState([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentZone, setCurrentZone] = useState(null);
  const [drawingMode, setDrawingMode] = useState(false);

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
    setDrawingMode(false);
    
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
      // Set canvas to native video dimensions to match YOLO coordinates correctly
      if (canvas.width !== videoRef.current.videoWidth) {
        canvas.width = videoRef.current.videoWidth || 640;
        canvas.height = videoRef.current.videoHeight || 480;
      }
      
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      const frameData = canvas.toDataURL('image/jpeg').split(',')[1];

      // Calculate scale to properly map drawn zones (on 640px wide scaled video max) into native pixels
      // However, we set the canvas directly above. If the zones are drawn relative to the scaled <svg>
      // To keep it simple, we assume the backend takes bounding box math relative to frame size.
      // Wait, we need to map SVG (which is scaled CSS) coordinates to Native Image coordinates for YOLO!
      const rect = svgRef.current.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;

      const scaledZones = zones.map(z => ({
        id: z.id,
        name: z.name,
        x: z.x * scaleX,
        y: z.y * scaleY,
        width: z.width * scaleX,
        height: z.height * scaleY
      }));

      // Send to backend
      const response = await cameraAPI.analyzeFrame(cameraId, frameData, scaledZones);
      
      // Update health data
      // For Frontend rendering overlay, we will draw YOLO detections which are in NATIVE pixel size. 
      // We must scale them back DOWN to the CSS size in the render block!
      const scaledDetections = (response.data.detections || []).map(det => ({
         ...det,
         box: [
           det.box[0] / scaleX,
           det.box[1] / scaleY,
           det.box[2] / scaleX,
           det.box[3] / scaleY
         ]
      }));

      setHealth({...response.data, detections: scaledDetections});
      setLastCaptureTime(new Date());

      // Add to history
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
        return updated.slice(-20);
      });
    } catch (err) {
      console.error('Error analyzing frame:', err);
    }
  };

  useEffect(() => {
    if (recording && !intervalRef.current) {
      captureAndAnalyze();
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
  }, [recording, zones]); // add zones to dependency so interval captures latest zones!

  // --- SVG Drawing Logic --- //
  const handleMouseDown = (e) => {
    if (!drawingMode) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setIsDrawing(true);
    setCurrentZone({ id: Date.now().toString(), name: `Zone ${zones.length + 1}`, x, y, width: 0, height: 0 });
  };

  const handleMouseMove = (e) => {
    if (!isDrawing || !currentZone) return;
    const rect = svgRef.current.getBoundingClientRect();
    const currentX = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const currentY = Math.max(0, Math.min(e.clientY - rect.top, rect.height));
    
    setCurrentZone((prev) => ({
      ...prev,
      width: currentX - prev.x,
      height: currentY - prev.y,
    }));
  };

  const handleMouseUp = () => {
    if (!isDrawing || !currentZone) return;
    setIsDrawing(false);
    
    let finalZone = { ...currentZone };
    if (finalZone.width < 0) {
      finalZone.x += finalZone.width;
      finalZone.width = Math.abs(finalZone.width);
    }
    if (finalZone.height < 0) {
      finalZone.y += finalZone.height;
      finalZone.height = Math.abs(finalZone.height);
    }
    
    if (finalZone.width > 20 && finalZone.height > 20) {
      setZones([...zones, finalZone]);
    }
    setCurrentZone(null);
  };
  
  const clearZones = () => {
    setZones([]);
  }

  const getHealthColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    if (score >= 40) return '#fd7e14';
    return '#ef4444';
  };

  const getHealthLabel = (score) => {
    if (score >= 80) return '✅ EXCELLENT';
    if (score >= 60) return '⚠️ GOOD';
    if (score >= 40) return '🟠 FAIR';
    return '🔴 POOR';
  };

  const peopleCount = health?.object_counts?.person || 0;
  const objectCountEntries = health ? Object.entries(health.object_counts || {}) : [];
  const zoneIntrusions = health?.zone_intrusions || [];
  const autoRiskScores = health?.auto_risk_scores || {};

  return (
    <div className="camera-container">
      <h2>📹 Camera Auto-Risk & Zoning</h2>
      <p className="subtitle">Real-time object tracking, zones, and security scoring</p>

      <div className="camera-section">
        <div className="video-wrapper" style={{ position: 'relative', width: '100%', maxWidth: '640px', margin: '0 auto', display: 'flex', borderRadius: '8px', overflow: 'hidden', backgroundColor: '#000' }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            style={{
              width: '100%',
              display: 'block'
            }}
          />
          <canvas
            ref={canvasRef}
            style={{ display: 'none' }}
          />
          
          {recording && (
             <svg
               ref={svgRef}
               style={{ 
                 position: 'absolute', 
                 top: 0, left: 0, 
                 width: '100%', height: '100%', 
                 pointerEvents: drawingMode ? 'auto' : 'none', 
                 cursor: drawingMode ? 'crosshair' : 'default',
                 zIndex: 10
               }}
               onMouseDown={handleMouseDown}
               onMouseMove={handleMouseMove}
               onMouseUp={handleMouseUp}
               onMouseLeave={handleMouseUp}
             >
               {/* Draw Zones */}
               {zones.map((zone) => (
                 <g key={zone.id}>
                   <rect x={zone.x} y={zone.y} width={zone.width} height={zone.height} fill="rgba(239, 68, 68, 0.15)" stroke="#ef4444" strokeWidth="2" strokeDasharray="5,5" />
                   <rect x={zone.x} y={zone.y - 20} width="80" height="20" fill="#ef4444" />
                   <text x={zone.x + 5} y={zone.y - 5} fill="white" fontSize="12" fontWeight="bold">{zone.name}</text>
                 </g>
               ))}
               
               {/* Draw Active Drawing Zone */}
               {currentZone && (
                 <rect
                   x={currentZone.width < 0 ? currentZone.x + currentZone.width : currentZone.x}
                   y={currentZone.height < 0 ? currentZone.y + currentZone.height : currentZone.y}
                   width={Math.abs(currentZone.width)}
                   height={Math.abs(currentZone.height)}
                   fill="rgba(59, 130, 246, 0.2)"
                   stroke="#3b82f6"
                   strokeWidth="2"
                   strokeDasharray="4"
                 />
               )}
               
               {/* Draw YOLO Detections */}
               {health?.detections?.map((det, idx) => {
                  const width = det.box[2] - det.box[0];
                  const height = det.box[3] - det.box[1];
                  const isPerson = det.class === 'person';
                  const color = isPerson ? '#f59e0b' : '#10b981';
                  
                  return (
                    <g key={`det-${idx}`}>
                      <rect x={det.box[0]} y={det.box[1]} width={width} height={height} fill="transparent" stroke={color} strokeWidth="2" />
                      <rect x={det.box[0]} y={det.box[1] - 18} width={isPerson ? 80 : 100} height="18" fill={color} />
                      <text x={det.box[0] + 4} y={det.box[1] - 4} fill="white" fontSize="11" fontWeight="bold">
                        {det.class.toUpperCase()} ({(det.confidence * 100).toFixed(0)}%)
                      </text>
                    </g>
                  );
               })}
             </svg>
          )}
        </div>

        <div className="camera-controls">
          {!recording ? (
            <button onClick={startCamera} className="btn-primary">📷 Start Camera</button>
          ) : (
            <>
              <button onClick={stopCamera} className="btn-danger">⏹️ Stop</button>
              
              <button 
                onClick={() => setDrawingMode(!drawingMode)} 
                className={`btn-secondary ${drawingMode ? 'active' : ''}`}
                style={{ backgroundColor: drawingMode ? '#3b82f6' : '', color: drawingMode ? 'white' : '' }}
              >
                {drawingMode ? 'Done Drawing' : '✏️ Draw Zone'}
              </button>
              
              {zones.length > 0 && (
                <button onClick={clearZones} className="btn-secondary">🗑️ Clear Zones</button>
              )}
            </>
          )}
        </div>
        
        {recording && drawingMode && (
           <p style={{ textAlign: 'center', color: '#666', marginTop: '10px' }}>
             Click and drag on the video to create a restricted Security Zone.
           </p>
        )}

        {recording && (
          <div className="recording-indicator">
            <span className="pulse"></span>
            <span>🔴 LIVE - Analyzing every 3s</span>
          </div>
        )}
      </div>
      
      {/* Zone Intrusion Alerts */}
      {zoneIntrusions.length > 0 && (
        <div className="issues-alert" style={{ backgroundColor: '#fef2f2', border: '1px solid #ef4444', animation: 'pulse 1.5s infinite' }}>
          <h3 style={{ color: '#ef4444' }}>🚨 ZONE INTRUSION DETECTED</h3>
          <ul>
            {zoneIntrusions.map((intrusion, idx) => (
              <li key={idx} style={{ color: '#991b1b', fontWeight: 'bold' }}>
                Person detected in {intrusion.zone_name} at {new Date(intrusion.timestamp).toLocaleTimeString()}
              </li>
            ))}
          </ul>
        </div>
      )}

      {health && (
        <>
          <div className="metrics-grid">
            {/* Auto-Risk Scoring Widget (Phase 1) */}
            <div className="metric-card" style={{ gridColumn: 'span 2', backgroundColor: '#f8fafc', borderLeft: '4px solid #3b82f6' }}>
              <h3>🤖 Auto-Risk Scoring</h3>
              <p style={{ fontSize: '12px', color: '#64748b', marginBottom: '10px' }}>Machine Generated Security Mappings</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div style={{ padding: '10px', backgroundColor: 'white', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>Lighting Quality Risk</div>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', color: autoRiskScores.lighting_quality === 'Poor' ? '#ef4444' : '#10b981' }}>
                    {autoRiskScores.lighting_quality || 'Unknown'}
                  </div>
                </div>
                
                <div style={{ padding: '10px', backgroundColor: 'white', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>CCTV Functionality Risk</div>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', color: autoRiskScores.cctv_functionality === 'Poor' ? '#ef4444' : '#10b981' }}>
                    {autoRiskScores.cctv_functionality || 'Unknown'}
                  </div>
                </div>
              </div>
            </div>

            <div className="metric-card">
              <h4>System Health</h4>
              <p className="value">{health.health_score.toFixed(0)}/100</p>
              <p className="status" style={{ color: getHealthColor(health.health_score) }}>
                {getHealthLabel(health.health_score)}
              </p>
            </div>

            <div className="metric-card">
              <h4>Status</h4>
              <p className="value">{health.status === 'online' ? '🟢' : '🔴'}</p>
              <p className="status">{health.status.toUpperCase()}</p>
            </div>
            
            <div className="metric-card">
              <h4>Brightness</h4>
              <p className="value">{health.metrics.brightness.toFixed(1)}</p>
              <p className="status">{health.metrics.brightness >= 50 && health.metrics.brightness <= 200 ? '✅ Good' : '⚠️ Poor'}</p>
            </div>
            
            <div className="metric-card">
              <h4>Blur Score</h4>
              <p className="value">{health.metrics.blur_score.toFixed(1)}</p>
              <p className="status">{health.metrics.blur_score >= 100 ? '✅ Sharp' : '⚠️ Blurry'}</p>
            </div>
          </div>

          {health.detection_enabled !== undefined && (
            <div className="detection-summary">
              <h3>🔍 Computer Vision Analytics</h3>
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
              <h3>⚠️ Health Issues Detected</h3>
              <ul>
                {health.issues.map((issue, idx) => (
                  <li key={idx}>{issue.replace(/_/g, ' ').toUpperCase()}</li>
                ))}
              </ul>
            </div>
          )}

          {healthHistory.length > 0 && (
            <div className="history-section">
              <h3>📈 Health Score Trend</h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={healthHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="score" stroke="#3b82f6" dot={false} name="Health Score" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
