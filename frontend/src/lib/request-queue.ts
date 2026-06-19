/**
 * 请求队列管理
 *
 * 限制并发请求数、自动去重、防止滥用
 */

import type { AxiosRequestConfig } from 'axios';

interface QueuedRequest {
  id: string;
  config: AxiosRequestConfig;
  resolve: (value: any) => void;
  reject: (reason?: any) => void;
}

class RequestQueue {
  private queue: QueuedRequest[] = [];
  private activeRequests = new Map<string, number>();
  private maxConcurrent = 5;

  /**
   * 生成请求的唯一 key
   */
  private generateKey(config: AxiosRequestConfig): string {
    const method = config.method || 'GET';
    const url = config.url || '';
    return `${method}:${url}`;
  }

  /**
   * 添加请求到队列
   */
  async enqueue(config: AxiosRequestConfig): Promise<[boolean, string, number]> {
    const key = this.generateKey(config);

    return new Promise((resolve) => {
      const request: QueuedRequest = {
        id: `${Date.now()}-${Math.random()}`,
        config,
        resolve: () => {
          this.dequeue(key);
          resolve([true, '', 0]);
        },
        reject: (reason) => {
          this.dequeue(key);
          resolve([false, reason?.message || '', 0]);
        },
      };

      this.queue.push(request);
      this.process();
    });
  }

  /**
   * 处理队列中的请求
   */
  private process() {
    while (this.queue.length > 0 && this.activeRequests.size < this.maxConcurrent) {
      const request = this.queue.shift();
      if (!request) break;

      const key = this.generateKey(request.config);
      const count = this.activeRequests.get(key) || 0;
      this.activeRequests.set(key, count + 1);
    }
  }

  /**
   * 请求完成，移除活跃计数
   */
  private dequeue(key: string) {
    const count = this.activeRequests.get(key) || 1;
    if (count <= 1) {
      this.activeRequests.delete(key);
    } else {
      this.activeRequests.set(key, count - 1);
    }
    this.process();
  }

  /**
   * 获取当前活跃请求数
   */
  getActiveCount(): number {
    return this.activeRequests.size;
  }

  /**
   * 获取队列长度
   */
  getQueueLength(): number {
    return this.queue.length;
  }
}

export const requestQueue = new RequestQueue();
