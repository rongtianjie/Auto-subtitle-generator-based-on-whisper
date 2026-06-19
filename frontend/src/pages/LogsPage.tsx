import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import LogViewer from '../components/LogViewer';

interface LogStats {
  total_entries: number;
  by_level: Record<string, number>;
  by_logger: Record<string, number>;
  errors_last_hour: number;
  warnings_last_hour: number;
}

const LogsPage: React.FC = () => {
  const [stats, setStats] = useState<LogStats | null>(null);
  const [activeTab, setActiveTab] = useState<'viewer' | 'request' | 'task'>('viewer');
  const [searchId, setSearchId] = useState('');
  const [loading, setLoading] = useState(false);

  const token = localStorage.getItem('token') || '';
  const apiUrl = 'http://localhost:8000/api/v1';

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/logs/stats?hours=24`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, [apiUrl, token]);

  useEffect(() => {
    void (async () => {
      await fetchStats();
    })();
    const interval = setInterval(() => {
      void fetchStats();
    }, 30000); // Refresh stats every 30s
    return () => clearInterval(interval);
  }, [fetchStats]);

  const getIconForLevel = (level: string) => {
    switch (level) {
      case 'ERROR':
      case 'CRITICAL':
        return <AlertCircle className="text-red-500" />;
      case 'WARNING':
        return <AlertTriangle className="text-yellow-500" />;
      case 'INFO':
        return <Info className="text-blue-500" />;
      default:
        return <CheckCircle className="text-green-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <h1 className="text-3xl font-bold text-gray-900">日志管理</h1>
          <p className="text-gray-600 mt-2">实时查看和分析应用日志</p>
        </div>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">总日志条数</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.total_entries}</p>
                </div>
                <Info className="text-blue-500" size={32} />
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">最近 1 小时错误</p>
                  <p className="text-3xl font-bold text-red-600">{stats.errors_last_hour}</p>
                </div>
                <AlertCircle className="text-red-500" size={32} />
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">最近 1 小时警告</p>
                  <p className="text-3xl font-bold text-yellow-600">{stats.warnings_last_hour}</p>
                </div>
                <AlertTriangle className="text-yellow-500" size={32} />
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">日志来源</p>
                  <p className="text-3xl font-bold text-blue-600">
                    {Object.keys(stats.by_logger).length}
                  </p>
                </div>
                <Info className="text-blue-500" size={32} />
              </div>
            </div>
          </div>

          {/* 日志级别分布 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold text-gray-900 mb-4">按日志级别分布</h3>
              <div className="space-y-3">
                {Object.entries(stats.by_level).map(([level, count]) => (
                  <div key={level} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getIconForLevel(level)}
                      <span className="text-gray-700">{level}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            level === 'ERROR' || level === 'CRITICAL' ? 'bg-red-500' :
                            level === 'WARNING' ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                          style={{
                            width: `${(count / stats.total_entries) * 100}%`
                          }}
                        />
                      </div>
                      <span className="text-gray-900 font-semibold w-12 text-right">
                        {count}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 主要日志来源 */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-bold text-gray-900 mb-4">主要日志来源</h3>
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {Object.entries(stats.by_logger)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 10)
                  .map(([logger, count]) => (
                    <div key={logger} className="flex items-center justify-between pb-2 border-b">
                      <span className="text-gray-700 truncate flex-1">{logger}</span>
                      <span className="text-gray-900 font-semibold ml-2">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 标签页 */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="bg-white rounded-lg shadow">
          <div className="border-b">
            <div className="flex gap-8 px-6">
              <button
                onClick={() => setActiveTab('viewer')}
                className={`py-4 px-4 font-medium border-b-2 transition-colors ${
                  activeTab === 'viewer'
                    ? 'text-blue-600 border-blue-600'
                    : 'text-gray-600 border-transparent hover:text-gray-900'
                }`}
              >
                日志浏览
              </button>
              <button
                onClick={() => setActiveTab('request')}
                className={`py-4 px-4 font-medium border-b-2 transition-colors ${
                  activeTab === 'request'
                    ? 'text-blue-600 border-blue-600'
                    : 'text-gray-600 border-transparent hover:text-gray-900'
                }`}
              >
                按请求查询
              </button>
              <button
                onClick={() => setActiveTab('task')}
                className={`py-4 px-4 font-medium border-b-2 transition-colors ${
                  activeTab === 'task'
                    ? 'text-blue-600 border-blue-600'
                    : 'text-gray-600 border-transparent hover:text-gray-900'
                }`}
              >
                按任务查询
              </button>
            </div>
          </div>

          <div className="p-6">
            {activeTab === 'viewer' && (
              <LogViewer apiUrl={apiUrl} token={token} />
            )}

            {activeTab === 'request' && (
              <div className="space-y-4">
                <div className="flex gap-4">
                  <input
                    type="text"
                    placeholder="输入 Request ID..."
                    value={searchId}
                    onChange={(e) => setSearchId(e.target.value)}
                    className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={async () => {
                      setLoading(true);
                      try {
                        const response = await fetch(
                          `${apiUrl}/logs/request/${searchId}`,
                          { headers: { 'Authorization': `Bearer ${token}` } }
                        );
                        if (response.ok) {
                          const data = await response.json();
                          console.log('Request logs:', data);
                        }
                      } finally {
                        setLoading(false);
                      }
                    }}
                    className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    {loading ? '搜索中...' : '搜索'}
                  </button>
                </div>
                {searchId && (
                  <div className="bg-gray-50 p-4 rounded-lg text-gray-600">
                    显示 Request ID 为 {searchId} 的日志记录
                  </div>
                )}
              </div>
            )}

            {activeTab === 'task' && (
              <div className="space-y-4">
                <div className="flex gap-4">
                  <input
                    type="text"
                    placeholder="输入 Task ID..."
                    value={searchId}
                    onChange={(e) => setSearchId(e.target.value)}
                    className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={async () => {
                      setLoading(true);
                      try {
                        const response = await fetch(
                          `${apiUrl}/logs/task/${searchId}`,
                          { headers: { 'Authorization': `Bearer ${token}` } }
                        );
                        if (response.ok) {
                          const data = await response.json();
                          console.log('Task logs:', data);
                        }
                      } finally {
                        setLoading(false);
                      }
                    }}
                    className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    {loading ? '搜索中...' : '搜索'}
                  </button>
                </div>
                {searchId && (
                  <div className="bg-gray-50 p-4 rounded-lg text-gray-600">
                    显示 Task ID 为 {searchId} 的日志记录
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
