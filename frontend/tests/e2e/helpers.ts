import { Page } from '@playwright/test';

/**
 * 等待任务完成（轮询状态）
 */
export async function waitForTaskCompletion(page: Page, taskId: string, maxWaitMs = 30000) {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitMs) {
    const taskRow = page.locator(`[data-task-id="${taskId}"]`);
    const status = await taskRow.locator('[data-status]').getAttribute('data-status');

    if (status === 'completed') {
      return true;
    }

    if (status === 'failed' || status === 'cancelled') {
      throw new Error(`Task ended with status: ${status}`);
    }

    await page.waitForTimeout(1000);
  }

  throw new Error(`Task did not complete within ${maxWaitMs}ms`);
}

/**
 * 上传文件到任务表单
 */
export async function uploadFile(page: Page, filePath: string) {
  // 通过 setInputFiles 设置文件
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(filePath);

  // 等待文件被处理（显示文件名或预览）
  await page.waitForTimeout(500);
}

/**
 * 获取任务输出列表
 */
export async function getTaskOutputs(page: Page, taskId: string) {
  const outputsContainer = page.locator(`[data-task-id="${taskId}"] [data-outputs]`);
  const outputs = await outputsContainer.locator('[data-format]').all();

  const result: { format: string; link: string }[] = [];
  for (const output of outputs) {
    const format = await output.getAttribute('data-format');
    const link = await output.locator('a').getAttribute('href');
    if (format && link) {
      result.push({ format, link });
    }
  }

  return result;
}

/**
 * 检查表单验证错误
 */
export async function getValidationErrors(page: Page): Promise<string[]> {
  const errors = await page.locator('[role="alert"]').all();
  const messages: string[] = [];

  for (const error of errors) {
    const text = await error.textContent();
    if (text) messages.push(text.trim());
  }

  return messages;
}

/**
 * 等待 API 响应
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  options?: { timeout?: number }
) {
  return page.waitForResponse(
    response => {
      const url = response.url();
      if (typeof urlPattern === 'string') {
        return url.includes(urlPattern);
      }
      return urlPattern.test(url);
    },
    options
  );
}

/**
 * 模拟网络延迟
 */
export async function slowDownNetwork(page: Page) {
  const client = await page.context().newCDPSession(page);
  await client.send('Network.enable');
  await client.send('Network.emulateNetworkConditions', {
    offline: false,
    downloadThroughput: 500 * 1024 / 8,
    uploadThroughput: 20 * 1024 / 8,
    latency: 400,
  });
}

/**
 * 模拟网络离线
 */
export async function goOffline(page: Page) {
  const client = await page.context().newCDPSession(page);
  await client.send('Network.emulateNetworkConditions', {
    offline: true,
    downloadThroughput: -1,
    uploadThroughput: -1,
    latency: 0,
  });
}

/**
 * 恢复网络
 */
export async function goOnline(page: Page) {
  const client = await page.context().newCDPSession(page);
  await client.send('Network.emulateNetworkConditions', {
    offline: false,
    downloadThroughput: -1,
    uploadThroughput: -1,
    latency: 0,
  });
}
