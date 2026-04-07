import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8003',
  withCredentials: true, 
});

// 1. Intercept BEFORE sending (Attach Token)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// 2. Intercept AFTER receiving (Catch Dead Tokens)
api.interceptors.response.use(
  (response) => response, // If successful, just return the data
  (error) => {
    // If the backend says 401 Unauthorized...
    if (error.response?.status === 401) {
      const detail = error.response?.data?.detail;
      
      // If it's OPA asking for Step-Up MFA, ignore it and let the Dashboard handle it!
      if (detail?.decision === 'step_up') {
        return Promise.reject(error);
      }
      
      // Otherwise, the token is dead. Nuke the session and redirect to login.
      console.warn("Session expired. Logging out.");
      localStorage.clear();
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

export default api;