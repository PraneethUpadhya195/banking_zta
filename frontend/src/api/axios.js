import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8003', // Your FastAPI backend
  // CRITICAL: This tells the browser to send your Device ID and MFA cookies!
  withCredentials: true, 
});

// Intercept every request before it leaves React to attach the Keycloak Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default api;