# Risk-Security Diagnostic - FastAPI + React

A modern web application for comprehensive facility security risk assessment, real-time camera monitoring, and anomaly detection.

## Project Structure

```
RSD-FastAPI-React/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application
│   │   ├── config.py               # Configuration settings
│   │   ├── db.py                   # Database setup
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   ├── crud.py                 # Database CRUD operations
│   │   ├── routes/
│   │   │   ├── risk.py             # Risk assessment endpoints
│   │   │   └── camera.py           # Camera health endpoints
│   │   └── services/
│   │       ├── risk_service.py     # Risk scoring logic
│   │       └── camera_service.py   # Camera health analysis
│   ├── requirements.txt
│   └── .env                        # Environment variables
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── apiClient.js        # Axios API client
│   │   ├── components/
│   │   │   ├── RiskForm.jsx        # Assessment form
│   │   │   ├── RiskResults.jsx     # Results display
│   │   │   ├── CameraHealth.jsx    # Camera monitoring
│   │   │   └── AnomalyReport.jsx   # Anomaly display
│   │   ├── pages/
│   │   │   ├── Home.jsx            # Landing page
│   │   │   └── Dashboard.jsx       # Main dashboard
│   │   ├── styles/
│   │   │   └── *.css               # Component styles
│   │   ├── App.jsx
│   │   └── index.jsx
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## Quick Start

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file (optional, uses defaults):
```bash
copy .env.example .env
```

5. Run the FastAPI server:
```bash
python -m uvicorn app.main:app --reload
```

The backend will be available at `http://localhost:8000`
API docs available at `http://localhost:8000/docs`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Features

### 1. **Risk Assessment**
- Comprehensive facility security evaluation across 5 major categories:
  - Physical Security
  - Access Control
  - Security Personnel
  - Incident History
  - Emergency Preparedness
- Weighted scoring system with overall risk calculation
- Risk level badges (LOW, MODERATE, HIGH, CRITICAL)

### 2. **Real-time Camera Monitoring**
- Browser-based camera capture via `getUserMedia`
- Automatic video quality analysis:
  - Blur detection (Laplacian variance)
  - Brightness analysis
  - Contrast measurement
  - Noise level estimation
  - Frame rate monitoring
  - Lens obstruction detection
- Health scoring (0-100)
- Issue detection with severity levels

### 3. **Anomaly Detection**
- Z-score based statistical anomaly detection
- Baseline comparison against historical metrics
- HIGH/MEDIUM severity classification
- Detailed human-readable explanations

### 4. **Data Persistence**
- SQLite database (default, can upgrade to PostgreSQL)
- Assessment history tracking
- Camera health history
- AI prediction storage

### 5. **Responsive UI**
- Mobile-friendly design
- Intuitive tab-based navigation
- Real-time chart visualization
- Progress indicators and loading states

## API Endpoints

### Risk Assessment
- `POST /api/risk/assess` - Create and score an assessment
- `GET /api/risk/assess/{id}` - Get assessment details
- `GET /api/risk/assessments` - List all assessments
- `POST /api/risk/anomaly/{id}` - Detect anomalies in assessment

### Camera Health
- `POST /api/camera/analyze` - Analyze a camera frame
- `GET /api/camera/health/{camera_id}` - Get camera status
- `GET /api/camera/history/{camera_id}` - Get camera health history

## Configuration

### Backend Environment Variables (`.env`)
```
DATABASE_URL=sqlite:///./rsd.db
DEBUG=True
API_TITLE=Risk-Security Diagnostic API
CAMERA_HISTORY_SIZE=100
MODEL_PATH=security_multiorg_model.pkl
```

### Frontend Environment Variables
```
REACT_APP_API_URL=http://localhost:8000/api
```

## Database Models

### Assessment
- `id`: Primary key
- `facility_name`: Facility name
- `input_data`: Raw form data (JSON)
- `category_scores`: Weighted scores by category
- `contributions`: Score contributions
- `overall_score`: Final risk score
- `risk_level`: Risk classification
- `created_at`, `updated_at`: Timestamps

### CameraHealth
- `id`: Primary key
- `camera_id`: Camera identifier
- `health_score`: 0-100 health score
- `blur_score`, `brightness`, `contrast`, `noise_level`, `fps`: Metrics
- `issues`: List of detected issues
- `created_at`: Timestamp

### AIPrediction
- `id`: Primary key
- `assessment_id`: Foreign key to Assessment
- `input_features`: ML feature vector (JSON)
- `unauthorized_access_prob`, `insider_threat_prob`, `emergency_failure_prob`, `perimeter_breach_prob`: Predictions
- `shap_values`: Feature importance explanations

## Development

### Running Both Backend and Frontend

**Terminal 1 (Backend):**
```bash
cd backend
python -m uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

Then visit `http://localhost:5173`

### Building for Production

**Backend:**
```bash
# Use gunicorn for production
pip install gunicorn
gunicorn app.main:app -w 4 -b 0.0.0.0:8000
```

**Frontend:**
```bash
npm run build
# Output in frontend/dist/
```

## Future Enhancements

- [ ] Multiple camera support with WebSocket streaming
- [ ] ML model integration (SHAP explanations)
- [ ] PDF report generation
- [ ] Email/SMS alerts
- [ ] Historical trend analysis
- [ ] User authentication
- [ ] Role-based access control
- [ ] Multi-facility support
- [ ] Custom thresholds configuration
- [ ] Video recording and playback

## Dependencies

### Backend
- FastAPI: Web framework
- SQLAlchemy: ORM
- OpenCV: Computer vision
- NumPy/Pandas: Data processing
- SHAP: ML explainability
- JobLib: Model serialization

### Frontend
- React 18: UI framework
- Axios: HTTP client
- Recharts: Data visualization
- Vite: Build tool
- Lucide React: Icons

## License

See LICENSE file

## Support

For issues or questions, please create an issue in the repository.
