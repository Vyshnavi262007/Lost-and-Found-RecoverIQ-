import axios from 'axios';

export const TOKEN_KEY = 'riq_token';
const api = axios.create({ baseURL: '/api' });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) cfg.headers.Authorization = `Token ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && localStorage.getItem(TOKEN_KEY)) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event('riq:logout'));
    }
    return Promise.reject(err);
  }
);

/** One readable string from any DRF error response. */
export function errorMessage(err, fallback = 'Something went wrong. Please try again.') {
  const d = err?.response?.data;
  if (!err?.response) return 'Cannot reach the server. Is the backend running?';
  if (typeof d === 'string') return d.length < 200 ? d : fallback;
  if (d?.detail) return d.detail;
  if (d && typeof d === 'object') {
    const parts = Object.entries(d).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : typeof v === 'object' ? JSON.stringify(v) : v}`);
    if (parts.length) return parts.join(' | ');
  }
  return fallback;
}

/** Field -> message map for inline form errors. */
export function fieldErrors(err) {
  const d = err?.response?.data;
  const out = {};
  if (d && typeof d === 'object' && !d.detail) {
    Object.entries(d).forEach(([k, v]) => { out[k] = Array.isArray(v) ? v.join(' ') : String(v); });
  }
  return out;
}

export default api;
