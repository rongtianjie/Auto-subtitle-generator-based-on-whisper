import React, { useState, useEffect, useRef } from 'react';
import { Pause, Play } from 'lucide-react';

interface LogStreamProps {
  apiUrl: string;
  token: string;
  requestId?: string;
  taskId?: string;
}

const LogStream: React.FC<LogStreamProps> = ({ apiUrl, token, requestId, taskId }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const [paused, setPaused] = useState(false);
  const [connected, setConnected] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // 构建 EventSource URL
    let url = `${apiUrl.replace('/api/v1', '')}/api/v1/tasks`;
    if (requestId) {
      url += `?request_id=${requestId}`;
    }
    if (taskId) {
      url += `${requestId ? '&' : '?'}task_id=${taskId}`;
    }
    url += '/stream';

    // 创建 EventSource
    const eventSource = new EventSource(url);

    eventSource.addEventListener('open', () => {
      setConnected(true);
    });

    eventSource.addEventListener('progress', (event) => {
      if (!paused) {
        try {
          const data = JSON.parse(event.data);
          setLogs(prev => [...prev, formatLogEntry(data)]);
        } catch (e) {
          console.error('Error parsing log event:', e);
        }
      }
    });

    eventSource.addEventListener('completed', (event) => {
      try {
        const data = JSON.parse(event.data);
        setLogs(prev => [...prev, formatLogEntry(data)]);
        eventSource.close();
        setConnected(false);
      } catch (e) {
        console.error('Error parsing completion event:', e);
      }
    });

    eventSource.addEventListener('error', (event) => {
      console.error('EventSource error:', event);
      setConnected(false);
      eventSource.close();
    });

    eventSourceRef.current = eventSource;

    return () => {
      eventSource.close();
    };
  }, [apiUrl, token, requestId, taskId]);

  useEffect(() => {
    if (!paused && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, paused]);

  const formatLogEntry = (data: any): string => {
    const timestamp = new Date(data.timestamp).toLocaleTimeString();
    return `[${timestamp}] ${data.message || data.progress_message || 'Progress update'}`;
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const downloadLogs = () => {
    const content = logs.join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs-${new Date().toISOString()}.txt`;
    a.click();
  };

  return (
    <div className="bg-black rounded-lg overflow-hidden shadow-lg">
      {/* 工具栏 */}
      <div className="bg-gray-900 border-b border-gray-700 p-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-white text-sm">
            {connected ? '实时流连接中' : '连接已断开'}
          </span>
          <span className="text-gray-400 text-sm">({logs.length} 条记录)</span>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setPaused(!paused)}
            className="px-3 py-1 bg-gray-700 text-white rounded hover:bg-gray-600 flex items-center gap-1"
          >
            {paused ? <Play size={16} /> : <Pause size={16} />}
            {paused ? '继续' : '暂停'}
          </button>
          <button
            onClick={downloadLogs}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            下载
          </button>
          <button
            onClick={clearLogs}
            className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
          >
            清空
          </button>
        </div>
      </div>

      {/* 日志内容 */}
      <div className="bg-black text-gray-300 p-4 overflow-y-auto max-h-96 font-mono text-sm">
        {logs.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            等待日志流...
          </div>
        ) : (
          <div>
            {logs.map((log, idx) => (
              <div key={idx} className="py-0.5">
                <span className="text-green-400">$</span> {log}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

export default LogStream;
