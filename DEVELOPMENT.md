# RSD-FastAPI-React Development Guide

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- npm or yarn

### Initial Setup

1. Clone or navigate to the project directory

2. **Backend Setup:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Frontend Setup:**
```bash
cd frontend
npm install
```

## Running in Development

### Start Backend
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs on: `http://localhost:8000`
Swagger docs: `http://localhost:8000/docs`

### Start Frontend (in another terminal)
```bash
cd frontend
npm run dev
```

Frontend runs on: `http://localhost:5173`

## Using Docker (Optional)

```bash
docker-compose up
```

This will start:
- Backend on `http://localhost:8000`
- Frontend on `http://localhost:5173`

## Project Structure Overview

### Backend (`/backend`)
- **app/main.py** - FastAPI application entry point
- **app/routes/** - API endpoint handlers
- **app/services/** - Business logic (risk scoring, camera analysis)
- **app/models.py** - Database models
- **app/schemas.py** - Request/response validation
- **app/crud.py** - Database operations
- **app/db.py** - Database configuration

### Frontend (`/frontend`)
- **src/pages/** - Full page components (Home, Dashboard)
- **src/components/** - Reusable components
- **src/api/** - API client configuration
- **src/styles/** - Component stylesheets
- **src/App.jsx** - Root component

## Making Changes

### Adding a Backend Endpoint

1. Create or update a route file in `app/routes/`
2. Import necessary services/crud functions
3. Define Pydantic schemas for request/response in `schemas.py`
4. Implement endpoint logic
5. Test via `http://localhost:8000/docs`

### Adding a Frontend Component

1. Create component in `src/components/` or `src/pages/`
2. Import and use in `App.jsx` or other components
3. Create corresponding CSS file in `src/styles/`
4. Use `apiClient` from `src/api/apiClient.js` to call backend

### Database Schema Changes

1. Update models in `app/models.py`
2. The database will auto-create tables on first run
3. For migrations: add Alembic when needed

## API Communication

Frontend calls backend via `axios` configured in `src/api/apiClient.js`.

Example usage in components:
```javascript
import { riskAPI } from '../api/apiClient';

// Create assessment
const response = await riskAPI.createAssessment(formData);

// Analyze camera
const result = await cameraAPI.analyzeFrame(cameraId, frameData);
```

## Testing

### Backend Testing
```bash
cd backend
pip install pytest
pytest
```

### Frontend Testing
```bash
cd frontend
npm test
```

## Deployment

### Backend (Gunicorn + Nginx)
```bash
pip install gunicorn
gunicorn app.main:app -w 4 -b 0.0.0.0:8000
```

### Frontend (Static Build)
```bash
npm run build
# Output in dist/ - serve with nginx/apache
```

## Troubleshooting

### Backend won't start
- Check port 8000 is free
- Verify Python version (3.9+)
- Run `pip install -r requirements.txt` again

### Frontend won't start
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version (16+)
- Port 5173 free

### Database errors
- Delete `rsd.db` to reset
- Check file permissions

### API calls failing
- Verify backend is running on 8000
- Check CORS settings in `app/config.py`
- Check browser console for error details

## Environment Variables

Create `.env` in backend/ with:
```
DATABASE_URL=sqlite:///./rsd.db
DEBUG=True
```

## Next Steps

1. ✅ Scaffold complete
2. Test backend endpoints via Swagger docs
3. Test frontend forms and components
4. Integrate ML model (when available)
5. Add authentication
6. Deploy to production

## Resources

- FastAPI Docs: https://fastapi.tiangolo.com
- React Docs: https://react.dev
- SQLAlchemy Docs: https://sqlalchemy.org
