import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api, { TOKEN_KEY } from '../api/client.js';

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!localStorage.getItem(TOKEN_KEY));

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/me/');
      setUser(data);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (localStorage.getItem(TOKEN_KEY)) refresh();
    const onLogout = () => setUser(null);
    window.addEventListener('riq:logout', onLogout);
    return () => window.removeEventListener('riq:logout', onLogout);
  }, [refresh]);

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login/', { email, password });
    localStorage.setItem(TOKEN_KEY, data.token);
    setUser(data.user);
    return data.user;
  };
  const adoptToken = (data) => { localStorage.setItem(TOKEN_KEY, data.token); setUser(data.user); };
  const logout = async () => {
    try { await api.post('/auth/logout/'); } catch { /* token may already be invalid */ }
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  };

  return <AuthCtx.Provider value={{ user, loading, login, logout, refresh, adoptToken, setUser }}>{children}</AuthCtx.Provider>;
}

export const homeFor = (user) => (user?.role === 'admin' ? '/admin' : user?.role === 'staff' ? '/staff' : '/dashboard');
