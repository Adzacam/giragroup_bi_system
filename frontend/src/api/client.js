import axios from 'axios';

const client = axios.create({
  baseURL: '', // handled by vite proxy for /api
  timeout: 60000, // 60 segundos por defecto (subidas pesadas usan timeout explícito de 10 min)
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('gira_token') || localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('gira_token');
      localStorage.removeItem('gira_user');
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      if (typeof window !== 'undefined' && window.location && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default client;
