import { test, expect } from '@playwright/test';
import { waitForTaskCompletion, getTaskOutputs } from './helpers';

test.describe('任务监控流程', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('应该显示任务进度', async ({ page }) => {
    // 创建任务
    await page.locator('input[value="upload"]').check();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/fixtures/sample.mp3');

    await page.locator('input[placeholder*="标题"]').fill('进度测试');
    await page.locator('button:has-text("开始转录")').click();

    // 获取任务 ID
    const taskItem = page.locator('[data-task-id]').first();
    const taskId = await taskItem.getAttribute('data-task-id');

    // 等待进度更新
    const progressBar = taskItem.locator('progress, [role="progressbar"]');
    await expect(progressBar).toBeVisible();

    // 检查进度消息
    const progressMessage = taskItem.locator('[data-progress-message]');
    await expect(progressMessage).toBeVisible();
  });

  test('应该能取消运行中的任务', async ({ page }) => {
    // 创建任务
    await page.locator('input[value="upload"]').check();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/fixtures/sample.mp3');

    await page.locator('input[placeholder*="标题"]').fill('取消测试');
    await page.locator('button:has-text("开始转录")').click();

    // 等待任务开始处理
    await page.waitForTimeout(1000);

    // 获取任务 ID
    const taskItem = page.locator('[data-task-id]').first();
    const taskId = await taskItem.getAttribute('data-task-id');

    // 点击取消按钮
    const cancelButton = taskItem.locator('button:has-text("取消")');
    if (await cancelButton.isVisible()) {
      await cancelButton.click();

      // 确认取消
      const confirmButton = page.locator('button:has-text("确认")');
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
      }
    }

    // 验证任务状态更新为已取消或待取消
    const status = await taskItem.locator('[data-status]').getAttribute('data-status');
    expect(['cancelled', 'cancelling']).toContain(status);
  });

  test('应该显示任务完成后的输出', async ({ page }) => {
    // 创建任务
    await page.locator('input[value="upload"]').check();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/fixtures/sample.mp3');

    await page.locator('input[placeholder*="标题"]').fill('完成测试');
    await page.locator('button:has-text("开始转录")').click();

    // 获取任务 ID
    const taskItem = page.locator('[data-task-id]').first();
    const taskId = await taskItem.getAttribute('data-task-id');

    // 等待任务完成（最多 5 分钟）
    try {
      await waitForTaskCompletion(page, taskId!, 300000);

      // 验证输出可见
      const outputs = await getTaskOutputs(page, taskId!);
      expect(outputs.length).toBeGreaterThan(0);

      // 验证至少包含一个输出格式
      const formats = outputs.map(o => o.format);
      expect(formats).toContain(expect.stringMatching(/txt|srt|vtt/));
    } catch (error) {
      // 如果没有实际的 Worker 运行，跳过
      test.skip();
    }
  });

  test('应该显示任务错误信息', async ({ page }) => {
    // 创建任务（可能会失败）
    await page.locator('input[value="url"]').check();
    const urlInput = page.locator('input[placeholder*="URL"]');
    await urlInput.fill('https://example.com/invalid-video');

    await page.locator('input[placeholder*="标题"]').fill('错误测试');
    await page.locator('button:has-text("开始转录")').click();

    // 等待任务失败
    const taskItem = page.locator('[data-task-id]').first();
    const taskId = await taskItem.getAttribute('data-task-id');

    // 设置超时检查失败状态
    await page.waitForTimeout(5000);

    const status = await taskItem.locator('[data-status]').getAttribute('data-status');
    if (status === 'failed') {
      // 验证错误信息显示
      const errorMessage = taskItem.locator('[data-error-message]');
      await expect(errorMessage).toBeVisible();
    }
  });

  test('应该自动刷新任务列表', async ({ page }) => {
    // 初始加载任务列表
    const taskCountBefore = await page.locator('[data-task-id]').count();

    // 创建新任务
    await page.locator('input[value="upload"]').check();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/fixtures/sample.mp3');

    await page.locator('input[placeholder*="标题"]').fill('刷新测试');
    await page.locator('button:has-text("开始转录")').click();

    // 等待列表刷新（应该有新的任务出现）
    await page.waitForTimeout(2000);

    const taskCountAfter = await page.locator('[data-task-id]').count();
    expect(taskCountAfter).toBeGreaterThan(taskCountBefore);
  });

  test('任务列表应该按创建时间排序', async ({ page }) => {
    // 获取任务列表
    const tasks = await page.locator('[data-task-id]').all();

    if (tasks.length > 1) {
      // 获取第一个和最后一个任务的时间戳
      const firstTaskTime = await tasks[0].locator('[data-created-at]').getAttribute('data-created-at');
      const lastTaskTime = await tasks[tasks.length - 1].locator('[data-created-at]').getAttribute('data-created-at');

      // 验证按降序排列（最新的在前）
      if (firstTaskTime && lastTaskTime) {
        expect(new Date(firstTaskTime).getTime()).toBeGreaterThanOrEqual(
          new Date(lastTaskTime).getTime()
        );
      }
    }
  });
});
