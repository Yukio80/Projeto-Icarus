import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * usePolling — executa uma função assíncrona no mount e em intervalos regulares,
 * gerenciando estados de loading, erro e dados. Cancela atualizações de estado
 * após o unmount para evitar memory leaks.
 *
 * @param {() => Promise<any>} fetcher Função assíncrona que retorna os dados.
 * @param {object} [options]
 * @param {number} [options.interval=15000] Intervalo de polling em ms. Use 0 para desativar.
 * @param {Array} [options.deps=[]] Dependências que reiniciam o polling quando mudam.
 * @param {boolean} [options.enabled=true] Se falso, o polling não inicia.
 * @returns {{ data: any, loading: boolean, error: string|null, refetch: () => Promise<void> }}
 */
export default function usePolling(fetcher, options = {}) {
  const { interval = 15000, deps = [], enabled = true } = options;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Mantém a referência mais recente do fetcher sem reiniciar o efeito.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const mountedRef = useRef(false);

  const load = useCallback(async () => {
    try {
      const result = await fetcherRef.current();
      if (mountedRef.current) {
        setData(result);
        setError(null);
      }
    } catch (e) {
      if (mountedRef.current) setError(e.message || 'Erro desconhecido');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    if (!enabled) {
      setLoading(false);
      return () => { mountedRef.current = false; };
    }

    setLoading(true);
    load();

    let id;
    if (interval > 0) {
      id = setInterval(load, interval);
    }

    return () => {
      mountedRef.current = false;
      if (id) clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, interval, enabled, ...deps]);

  return { data, loading, error, refetch: load };
}
