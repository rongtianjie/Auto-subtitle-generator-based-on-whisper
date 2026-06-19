import { useEffect, useRef, useState, useCallback } from 'react';
import { taskApi } from '@/lib/api';

interface SSEProgress {
  status: string;
  progress: number;
  message: string | null;
  error_message: string | null;
  queue_position: number | null;
  estimated_seconds: number | null;
}

export function useSSE(taskId: string | null) {
  const [progress, setProgress] = useState<SSEProgress | null>(null);
  const [done, setDone] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const lastActivityRef = useRef<number>(0);
  const doneRef = useRef(false);
  const connectedRef = useRef(false);
  const connectRef = useRef<(url: string) => void>(() => {});
  const heartbeatCheckIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const connect = useCallback((url: string) => {
    try {
      const es = new EventSource(url);
      eventSourceRef.current = es;
      reconnectAttemptsRef.current = 0;
      doneRef.current = false;

      es.onopen = () => {
        connectedRef.current = true;
        setConnected(true);
        setError(null);
        lastActivityRef.current = Date.now();
      };

      es.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        setProgress(data);
        lastActivityRef.current = Date.now();
      });

      es.addEventListener('keepalive', () => {
        // 心跳包，仅用于保持连接
        lastActivityRef.current = Date.now();
      });

      es.addEventListener('completed', (event) => {
        const data = JSON.parse(event.data);
        setProgress(data);
        doneRef.current = true;
        setDone(true);
        connectedRef.current = false;
        setConnected(false);
        es.close();
      });

      es.addEventListener('failed', (event) => {
        const data = JSON.parse(event.data);
        setProgress(data);
        doneRef.current = true;
        setDone(true);
        connectedRef.current = false;
        setConnected(false);
        es.close();
      });

      es.addEventListener('cancelled', (event) => {
        const data = JSON.parse(event.data);
        setProgress(data);
        doneRef.current = true;
        setDone(true);
        connectedRef.current = false;
        setConnected(false);
        es.close();
      });

      es.addEventListener('error', () => {
        connectedRef.current = false;
        setConnected(false);
        setError('连接已断开');
        es.close();

        // 自动重连（最多 3 次）
        if (reconnectAttemptsRef.current < 3) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.pow(2, reconnectAttemptsRef.current - 1) * 1000; // 指数退避: 1s, 2s, 4s
          setTimeout(() => {
            if (!doneRef.current) {
              connectRef.current(url);
            }
          }, delay);
        } else {
          setError('连接已断开，请刷新页面重试');
          doneRef.current = true;
          setDone(true);
        }
      });

      // 启动心跳检测（15秒无数据则认为连接已死）
      if (heartbeatCheckIntervalRef.current) {
        clearInterval(heartbeatCheckIntervalRef.current);
      }

      heartbeatCheckIntervalRef.current = setInterval(() => {
        const now = Date.now();
        const idleTime = (now - lastActivityRef.current) / 1000;
        if (idleTime > 15 && connectedRef.current) {
          setError('连接超时');
          es.close();
          connectedRef.current = false;
          setConnected(false);

          // 尝试重连
          if (reconnectAttemptsRef.current < 3) {
            reconnectAttemptsRef.current += 1;
            setTimeout(() => {
              if (!doneRef.current) {
                connectRef.current(url);
              }
            }, 1000 * Math.pow(2, reconnectAttemptsRef.current - 1));
          }
        }
      }, 5000); // 每 5 秒检查一次
    } catch {
      setError('连接失败');
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    if (!taskId) return;

    doneRef.current = false;
    queueMicrotask(() => setDone(false));

    const url = taskApi.getStreamUrl(taskId);
    queueMicrotask(() => {
      connect(url);
    });

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (heartbeatCheckIntervalRef.current) {
        clearInterval(heartbeatCheckIntervalRef.current);
      }
    };
  }, [taskId, connect]);

  return { progress, done, connected, error };
}
