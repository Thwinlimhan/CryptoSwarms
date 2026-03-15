import { useState, useEffect, useCallback, useRef } from 'react';
import { getWebSocketBaseUrl } from '../config';

const MIN_RECONNECT_MS = 3000;
const MAX_RECONNECT_MS = 30000;
const BACKOFF_MULTIPLIER = 1.5;

export function useWebSocket<T = unknown>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const reconnectDelayRef = useRef(MIN_RECONNECT_MS);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    const base = getWebSocketBaseUrl();
    const url = `${base.replace(/\/$/, '')}${path.startsWith('/') ? path : `/${path}`}`;
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      if (!mountedRef.current) return;
      setIsConnected(true);
      reconnectDelayRef.current = MIN_RECONNECT_MS;
      if (reconnectTimeoutRef.current !== undefined) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = undefined;
      }
    };

    socket.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const message = JSON.parse(event.data) as T;
        setData(message);
      } catch {
        // ignore non-JSON (e.g. pong)
      }
    };

    socket.onclose = () => {
      if (!mountedRef.current) return;
      setIsConnected(false);
      socketRef.current = null;
      if (!mountedRef.current) return;
      const delay = reconnectDelayRef.current;
      reconnectDelayRef.current = Math.min(
        Math.floor(delay * BACKOFF_MULTIPLIER),
        MAX_RECONNECT_MS
      );
      reconnectTimeoutRef.current = window.setTimeout(connect, delay);
    };

    socket.onerror = () => {
      // Rely on onclose for reconnect; avoid spamming console when backend is down
      socket.close();
    };
  }, [path]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current !== undefined) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = undefined;
      }
      const sock = socketRef.current;
      if (sock != null) {
        sock.onclose = null;
        sock.onerror = null;
        sock.onmessage = null;
        sock.onopen = null;
        sock.close();
        socketRef.current = null;
      }
    };
  }, [connect]);

  const send = useCallback((message: unknown) => {
    const sock = socketRef.current;
    if (sock?.readyState === WebSocket.OPEN) {
      sock.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }, []);

  return { data, isConnected, send };
}
