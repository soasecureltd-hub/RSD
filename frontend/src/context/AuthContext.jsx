import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../api/apiClient';

const AuthContext = createContext(null);
const TOKEN_KEY = 'rsd_token';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = !!token && !!user;

  const fetchMe = useCallback(async (accessToken) => {
    try {
      const res = await apiClient.get('/auth/me', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      setUser(res.data);
    } catch {
      setToken(null);
      setUser(null);
      localStorage.removeItem(TOKEN_KEY);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchMe(token).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  // Listen for 401 events dispatched by the axios interceptor
  useEffect(() => {
    const handler = () => {
      setToken(null);
      setUser(null);
      localStorage.removeItem(TOKEN_KEY);
    };
    window.addEventListener('rsd:auth:logout', handler);
    return () => window.removeEventListener('rsd:auth:logout', handler);
  }, []);

  const login = async (email, password) => {
    const res = await apiClient.post('/auth/login/json', { email, password });
    const accessToken = res.data.access_token;
    localStorage.setItem(TOKEN_KEY, accessToken);
    setToken(accessToken);
    await fetchMe(accessToken);
  };

  const register = async (email, password, full_name) => {
    try {
      await apiClient.post('/auth/register', { email, password, full_name });
    } catch (err) {
      const detail = err.response?.data?.detail || 'Registration failed';
      throw new Error(detail);
    }
    // Registration succeeded — now sign in. A failure here is a login error, not a registration error.
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
