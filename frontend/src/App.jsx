import React, { useState } from 'react';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import CameraHealth from './components/CameraHealth';
import './styles/App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('home');

  const navigateTo = (page) => {
    setCurrentPage(page);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1 onClick={() => navigateTo('home')} style={{ cursor: 'pointer' }}>
          🔐 RSD
        </h1>
        <nav className="nav-menu">
          <button onClick={() => navigateTo('home')}>Home</button>
          <button onClick={() => navigateTo('dashboard')}>Assessment</button>
          <button onClick={() => navigateTo('camera')}>Camera</button>
        </nav>
      </header>

      <main className="app-main">
        {currentPage === 'home' && <Home onNavigate={navigateTo} />}
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'camera' && <CameraHealth />}
      </main>

      <footer className="app-footer">
        <p>Risk-Security Diagnostic &copy; 2024 | All Rights Reserved</p>
      </footer>
    </div>
  );
}

export default App;
