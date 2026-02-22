import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({ baseURL: API_URL, timeout: 30000 });

api.interceptors.response.use(
  (r) => r,
  (err) => {
    console.error(`[Fred] ${err.config?.method?.toUpperCase()} ${err.config?.url}:`, err.message);
    return Promise.reject(err);
  }
);

export default api;
export { API_URL };
