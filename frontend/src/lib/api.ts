import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 秒超时
});

// 请求拦截器：注入 token 和自动重试
api.interceptors.request.use(
  (config) => {
    const token =
      localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 添加重试计数（仅用于追踪）
    if (!config.headers['x-retry-count']) {
      config.headers['x-retry-count'] = 0;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理错误响应、超时和自动重试
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;

    // 处理 API 错误响应
    if (error.response) {
      const data = error.response.data;
      const status = error.response.status;

      // 提取标准错误格式
      const errorMessage = data?.message || error.message || "Unknown error";
      const errorCode = data?.error_code || `HTTP_${status}`;

      // Token 过期或无效 - 清除存储
      if (status === 401 || errorCode === "TOKEN_EXPIRED" || errorCode === "UNAUTHORIZED") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("refresh_token");
      }

      // 创建标准化错误对象
      error.isApiError = true;
      error.errorCode = errorCode;
      error.statusCode = status;
      error.userMessage = errorMessage;
      error.details = data?.details;
    } else if (error.code === 'ECONNABORTED') {
      // 超时错误
      error.isTimeoutError = true;
      error.userMessage = "请求超时（30秒），请重试或检查网络";

      // 重试超时请求 (GET 请求)
      if (config && config.method === 'get') {
        const retryCount = parseInt(config.headers?.['x-retry-count'] || 0);
        if (retryCount < 3) {
          config.headers['x-retry-count'] = retryCount + 1;
          // 指数退避: 1s, 2s, 4s
          const delay = Math.pow(2, retryCount) * 1000;
          await new Promise((resolve) => setTimeout(resolve, delay));
          return api.request(config);
        }
      }
    } else if (error.request) {
      // 网络错误（无响应）
      error.isNetworkError = true;
      error.userMessage = "网络连接失败，请检查网络后重试";

      // 重试网络错误 (GET 请求)
      if (config && config.method === 'get') {
        const retryCount = parseInt(config.headers?.['x-retry-count'] || 0);
        if (retryCount < 3) {
          config.headers['x-retry-count'] = retryCount + 1;
          const delay = Math.pow(2, retryCount) * 1000;
          await new Promise((resolve) => setTimeout(resolve, delay));
          return api.request(config);
        }
      }
    } else {
      // 请求配置错误
      error.userMessage = "请求配置错误";
    }

    return Promise.reject(error);
  }
);

export default api;

// ===== 认证 API =====
export const authApi = {
  register: (data: { username: string; email: string; password: string }) =>
    api.post('/auth/register', data),

  login: (data: { username: string; password: string }) =>
    api.post('/auth/login', data),

  refresh: (refresh_token: string) =>
    api.post('/auth/refresh', { refresh_token }),

  getMe: () => api.get('/auth/me'),

  checkAdminExists: () => api.get('/auth/admin-exists'),

  registerAdmin: (data: { username: string; email: string; password: string }) =>
    api.post('/auth/register-admin', data),
};

// ===== 任务 API =====
export const taskApi = {
  getDefaults: () => api.get('/tasks/defaults'),

  create: (formData: FormData) =>
    api.post('/tasks', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get('/tasks', { params }),

  get: (id: string) => api.get(`/tasks/${id}`),

  delete: (id: string) => api.delete(`/tasks/${id}`),

  cancel: (id: string) => api.put(`/tasks/${id}/cancel`),

  getOutputs: (id: string) => api.get(`/tasks/${id}/outputs`),

  getQueueStatus: () => api.get('/tasks/queue'),

  getStreamUrl: (id: string) => `/api/v1/tasks/${id}/stream`,

  downloadUrl: (taskId: string, outputId: string) =>
    `/api/v1/tasks/${taskId}/outputs/${outputId}/download`,
};

// ===== 健康检查 API =====
export const healthApi = {
  check: () => api.get('/health'),
  ready: () => api.get('/health/ready'),
};

// ===== 管理后台 API =====
export const adminApi = {
  listTasks: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get('/admin/tasks', { params }),

  retryTask: (id: string) => api.put(`/admin/tasks/${id}/retry`),

  cancelTask: (id: string) => api.put(`/admin/tasks/${id}/cancel`),

  deleteTask: (id: string) => api.delete(`/admin/tasks/${id}`),

  listUsers: (params?: { q?: string; page?: number; page_size?: number }) =>
    api.get('/admin/users', { params }),

  toggleUserActive: (userId: string) =>
    api.put(`/admin/users/${userId}/toggle-active`),

  deleteUser: (userId: string) =>
    api.delete(`/admin/users/${userId}`),

  resetPassword: (userId: string) =>
    api.post(`/admin/users/${userId}/reset-password`),

  listUserTasks: (userId: string, params?: { page?: number; page_size?: number; status?: string }) =>
    api.get(`/admin/users/${userId}/tasks`, { params }),

  updateUserRole: (userId: string, role: string) =>
    api.put(`/admin/users/${userId}/role`, { role }),

  getConfig: () => api.get('/admin/config'),

  updateConfig: (key: string, value: unknown, description?: string) =>
    api.put(`/admin/config/${key}`, { value, description }),

  getStats: () => api.get('/admin/stats'),

  getHealth: () => api.get('/admin/health'),

  testLlm: (data?: { base_url?: string; api_key?: string; model?: string }) =>
    api.post('/admin/llm/test', data || {}),

  fetchLlmModels: (data: { base_url: string; api_key: string }) =>
    api.post('/admin/llm/fetch-models', data),

  listLogFiles: () => api.get('/admin/logs'),

  getLogContent: (filename: string, tail?: number) =>
    api.get(`/admin/logs/${encodeURIComponent(filename)}`, { params: { tail } }),

  getLogStreamUrl: (filename: string) =>
    `/api/v1/admin/logs/${encodeURIComponent(filename)}/stream`,

  listFiles: (params?: { q?: string; file_type?: string; task_id?: string; page?: number; page_size?: number; sort_by?: string; sort_order?: string }) =>
    api.get('/admin/files', { params }),

  deleteFiles: (data: { file_ids: string[]; mode: 'soft' | 'hard' }) =>
    api.delete('/admin/files', { data }),

  getFileDownloadUrl: (fileId: string) =>
    `/api/v1/admin/files/${encodeURIComponent(fileId)}/download`,

  getFilePreviewUrl: (fileId: string) =>
    `/api/v1/admin/files/${encodeURIComponent(fileId)}/preview`,
};

// ===== 模型管理 API =====
export const modelApi = {
  list: () => api.get('/models'),

  download: (name: string) => api.post(`/models/${name}/download`),

  deleteAll: () => api.delete('/models'),
};
