import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Filter, Download, RefreshCw, ChevronDown } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  logger: string;
  request_id?: string;
  user_id?: string;
  task_id?: string;
  duration_ms?: number;
}

interface LogViewerProps {
  apiUrl: string;
  token: string;
}

export const LogViewer: React.FC<LogViewerProps> = ({ apiUrl, token }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('');
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const applyFilters = useCallback((logsToFilter: LogEntry[], query: string) => {
    const filtered = logsToFilter.filter(log => {
      const matchesQuery = query === '' ||
        log.message.toLowerCase().includes(query.toLowerCase()) ||
        log.logger.toLowerCase().includes(query.toLowerCase());

      const matchesLevel = selectedLevel === '' || log.level === selectedLevel;

      return matchesQuery && matchesLevel;
    });

    setFilteredLogs(filtered);
  }, [selectedLevel]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedLevel) params.append('level', selectedLevel);
      params.append('limit', '100');

      const response = await fetch(
        `${apiUrl}/logs/recent?${params}`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (!response.ok) throw new Error('Failed to fetch logs');

      const data = await response.json();
      setLogs(data);
      applyFilters(data, searchQuery);
    } catch (error) {
      console.error('Error fetching logs:', error);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, selectedLevel, searchQuery, applyFilters]);

  useEffect(() => {
    queueMicrotask(() => applyFilters(logs, searchQuery));
  }, [searchQuery, selectedLevel, logs, applyFilters]);

  useEffect(() => {
    const interval = setInterval(fetchLogs, 5000); // Auto-refresh every 5s
    return () => clearInterval(interval);
  }, [fetchLogs]);

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll]);

  const searchLogs = async () => {
    if (!searchQuery.trim()) {
      fetchLogs();
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${apiUrl}/logs/search?keyword=${encodeURIComponent(searchQuery)}&limit=100`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      setLogs(data);
      applyFilters(data, searchQuery);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportLogs = () => {
    const csv = [
      ['Timestamp', 'Level', 'Logger', 'Message', 'Request ID', 'Task ID', 'Duration (ms)'].join(','),
      ...filteredLogs.map(log =>
        [
          log.timestamp,
          log.level,
          log.logger,
          `"${log.message.replace(/"/g, '""')}"`,
          log.request_id || '',
          log.task_id || '',
          log.duration_ms || ''
        ].join(',')
      )
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs-${new Date().toISOString()}.csv`;
    a.click();
  };

  const getLevelColor = (level: string) => {
    const colors: Record<string, string> = {
      'DEBUG': 'bg-gray-100 text-gray-800',
      'INFO': 'bg-blue-100 text-blue-800',
      'WARNING': 'bg-yellow-100 text-yellow-800',
      'ERROR': 'bg-red-100 text-red-800',
      'CRITICAL': 'bg-red-200 text-red-900'
    };
    return colors[level] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="w-full h-full bg-white rounded-lg shadow-lg p-6">
      <div className="space-y-4">
        {/* 工具栏 */}
        <div className="flex gap-4 flex-wrap">
          <div className="flex-1 min-w-[300px] relative">
            <input
              type="text"
              placeholder="搜索日志关键词..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && searchLogs()}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Search className="absolute right-3 top-2.5 text-gray-400" size={20} />
          </div>

          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">所有级别</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>

          <button
            onClick={fetchLogs}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 flex items-center gap-2"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            刷新
          </button>

          <button
            onClick={exportLogs}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 flex items-center gap-2"
          >
            <Download size={18} />
            导出
          </button>

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
              autoScroll ? 'bg-purple-500 text-white' : 'bg-gray-200 text-gray-800'
            }`}
          >
            <Filter size={18} />
            {autoScroll ? '自动滚动' : '手动滚动'}
          </button>
        </div>

        {/* 统计信息 */}
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div className="bg-blue-50 p-3 rounded">
            <div className="text-gray-600">总条数</div>
            <div className="text-2xl font-bold text-blue-600">{filteredLogs.length}</div>
          </div>
          <div className="bg-red-50 p-3 rounded">
            <div className="text-gray-600">错误</div>
            <div className="text-2xl font-bold text-red-600">
              {filteredLogs.filter(l => l.level === 'ERROR').length}
            </div>
          </div>
          <div className="bg-yellow-50 p-3 rounded">
            <div className="text-gray-600">警告</div>
            <div className="text-2xl font-bold text-yellow-600">
              {filteredLogs.filter(l => l.level === 'WARNING').length}
            </div>
          </div>
          <div className="bg-green-50 p-3 rounded">
            <div className="text-gray-600">成功</div>
            <div className="text-2xl font-bold text-green-600">
              {filteredLogs.filter(l => l.level === 'INFO').length}
            </div>
          </div>
        </div>

        {/* 日志列表 */}
        <div className="bg-gray-900 rounded-lg p-4 overflow-y-auto max-h-[600px] font-mono text-sm">
          {filteredLogs.length === 0 ? (
            <div className="text-gray-400 text-center py-8">
              没有日志记录
            </div>
          ) : (
            <div className="space-y-2">
              {filteredLogs.map((log, idx) => (
                <div
                  key={idx}
                  className="space-y-1 cursor-pointer hover:bg-gray-800 p-2 rounded transition"
                  onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
                >
                  {/* 日志行摘要 */}
                  <div className="flex items-start gap-3">
                    <ChevronDown
                      size={16}
                      className={`text-gray-500 flex-shrink-0 transition-transform ${
                        expandedIndex === idx ? 'rotate-180' : ''
                      }`}
                    />
                    <span className="text-gray-400">{log.timestamp}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${getLevelColor(log.level)}`}>
                      {log.level}
                    </span>
                    <span className="text-gray-300">[{log.logger}]</span>
                    <span className="text-white flex-1 truncate">{log.message}</span>
                  </div>

                  {/* 展开的详细信息 */}
                  {expandedIndex === idx && (
                    <div className="ml-6 bg-gray-800 p-3 rounded border-l-2 border-blue-500 space-y-1 text-gray-300 text-xs">
                      {log.request_id && (
                        <div>
                          <span className="text-blue-400">Request ID:</span>
                          <span className="ml-2 font-mono">{log.request_id}</span>
                        </div>
                      )}
                      {log.user_id && (
                        <div>
                          <span className="text-blue-400">User ID:</span>
                          <span className="ml-2 font-mono">{log.user_id}</span>
                        </div>
                      )}
                      {log.task_id && (
                        <div>
                          <span className="text-blue-400">Task ID:</span>
                          <span className="ml-2 font-mono">{log.task_id}</span>
                        </div>
                      )}
                      {log.duration_ms && (
                        <div>
                          <span className="text-blue-400">Duration:</span>
                          <span className="ml-2 font-mono">{log.duration_ms.toFixed(2)}ms</span>
                        </div>
                      )}
                      <div className="mt-2 text-gray-400">
                        <span className="text-blue-400">Full Message:</span>
                        <div className="mt-1 p-2 bg-gray-900 rounded max-h-[200px] overflow-y-auto">
                          {log.message}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          )}
        </div>

        {/* 加载状态 */}
        {loading && (
          <div className="text-center text-gray-500">
            加载中...
          </div>
        )}
      </div>
    </div>
  );
};

export default LogViewer;
