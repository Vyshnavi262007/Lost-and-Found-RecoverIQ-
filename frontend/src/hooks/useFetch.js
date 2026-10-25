import { useCallback, useEffect, useState } from 'react';
import api, { errorMessage } from '../api/client.js';

/** GET helper: returns { data, loading, error, reload, setData }. `url` null skips the request. */
export default function useFetch(url, params) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(!!url);
  const [error, setError] = useState('');
  const key = JSON.stringify(params || {});

  const load = useCallback(async () => {
    if (!url) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.get(url, { params: JSON.parse(key) });
      setData(res.data);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [url, key]);

  useEffect(() => { load(); }, [load]);
  return { data, loading, error, reload: load, setData };
}
