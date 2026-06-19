/**
 * 从 axios 错误中提取用户友好的错误信息。
 * 支持新的标准错误格式和网络错误处理。
 */
type ApiErrorLike = {
  userMessage?: string;
  response?: {
    data?: {
      message?: unknown;
      error_code?: unknown;
    };
    status?: number;
  };
  code?: string;
  isTimeoutError?: boolean;
  isNetworkError?: boolean;
  errorCode?: string;
};

export function extractApiError(err: unknown, fallback: string): string {
  const error = err as ApiErrorLike;
  // 使用标准化的 userMessage（来自拦截器）
  if (error.userMessage) {
    return error.userMessage;
  }

  // 新格式：标准错误响应
  if (error.response) {
    const data = error.response.data;
    const status = error.response.status;

    // 优先使用后端返回的 message 字段
    if (data?.message && typeof data.message === 'string') {
      return data.message;
    }

    // 按状态码兜底
    if (status === 401 || status === 403) {
      return fallback;
    }
    if (status === 429) {
      return '操作过于频繁，请稍后再试';
    }
    if (typeof status === 'number' && status >= 500) {
      return '服务器内部错误，请稍后重试';
    }
    if (status === 400) {
      return '请求参数有误，请检查输入';
    }
  }

  // 超时错误
  if (error.code === 'ECONNABORTED' || error.isTimeoutError) {
    return '请求超时（30秒），请检查网络后重试';
  }

  // 网络错误
  if (error.isNetworkError || !error.response) {
    return '网络连接失败，请检查网络后重试';
  }

  return fallback;
}

/**
 * 检查错误是否可重试
 */
export function isRetriableError(err: unknown): boolean {
  const error = err as ApiErrorLike;
  // 网络错误和超时可重试
  if (error.isNetworkError || error.isTimeoutError) {
    return true;
  }

  // 5xx 服务器错误可重试
  if (error.response?.status && error.response.status >= 500) {
    return true;
  }

  // 429 Too Many Requests 可重试（但应该添加延迟）
  if (error.response?.status === 429) {
    return true;
  }

  return false;
}

/**
 * 获取错误代码（用于分析和日志）
 */
export function getErrorCode(err: unknown): string {
  const error = err as ApiErrorLike;

  if (error.errorCode) {
    return error.errorCode;
  }

  if (error.response?.data?.error_code && typeof error.response.data.error_code === 'string') {
    return error.response.data.error_code;
  }

  if (error.response?.status) {
    return `HTTP_${error.response.status}`;
  }

  if (error.code) {
    return error.code;
  }

  return 'UNKNOWN_ERROR';
}
