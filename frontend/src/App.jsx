import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AssessmentProvider } from './context/AssessmentContext';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Register from './pages/Register';
import './styles/App.css';

function AppShell() {
  const { isAuthenticated, loading, user, logout } = useAuth();
  const [currentPage, setCurrentPage] = useState('home');
  const [authPage, setAuthPage] = useState('login'); // 'login' | 'register'

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f2744' }}>
        <p style={{ color: '#fff', fontSize: '1.2rem' }}>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return authPage === 'login'
      ? <Login onSwitchToRegister={() => setAuthPage('register')} />
      : <Register onSwitchToLogin={() => setAuthPage('login')} />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 onClick={() => setCurrentPage('home')} style={{ cursor: 'pointer' }}>🔐 RSD</h1>
        <nav className="nav-menu">
          <button onClick={() => setCurrentPage('home')}>Home</button>
          <button onClick={() => setCurrentPage('dashboard')}>Assessment</button>
        </nav>
        <div className="nav-user">
          <span className="nav-email">{user?.email}</span>
          <button onClick={logout} className="btn-logout">Sign Out</button>
        </div>
      </header>

      <main className="app-main">
        {currentPage === 'home' && <Home onNavigate={setCurrentPage} />}
        {currentPage === 'dashboard' && <Dashboard />}
      </main>

      <footer className="app-footer">
        <p>Risk-Security Diagnostic &copy; 2024 | All Rights Reserved</p>
      </footer>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AssessmentProvider>
        <AppShell />
      </AssessmentProvider>
    </AuthProvider>
  );
}

export default App;
