import axios from 'axios';
import { API_URL } from '../config';

const client = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const token = import.meta.env.VITE_API_TOKEN;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.error || err.response?.data?.detail || err.message;
    console.error(`[API] ${err.config?.method?.toUpperCase()} ${err.config?.url}: ${msg}`);
    return Promise.reject(err);
  }
);

export default client;
