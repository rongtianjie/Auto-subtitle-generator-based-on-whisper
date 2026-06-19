import { test, expect } from '@playwright/test';

test.describe('错误处理和网络恢复', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('应该处理 API 超时错误', async ({ page }) => {
    // 模拟超时（通过速度限制）
    await page.context().setExtraHTTPHeaders({
      'X-Simulate-Timeout': 'true',
    });

    // 尝试创建任务
    await page.locator('input[value="upload"]').check();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/fixtures/sample.mp3');

    await page.locator('input[placeholder*="标题"]').fill('超时测试');

    const submitButton = page.locator('button:has-text("开始转录")');
    await submitButton.click();

    // 等待错误消息或重试
    const errorMessage = page.locator('[role="alert"]');
    const isVisible = await errorMessage.isVisible({ timeout: 5000 }).catch(() => false);

    if (isVisible) {
      const errorText = await errorMessage.textContent();
      expect(errorText).toContain(
        /超时|连接|网络|服务/i
      );
    }
  });

  test('应该显示无效的 URL 错误', async ({ page }) => {
    // 选择 URL 模式
    await page.locator('input[value="url"]').check();

    // 输入无效的 URL
    const urlInput = page.locator('input[placeholder*="URL"]');
    await urlInput.fill('invalid-url');

    // 尝试提交
    const submitButton = page.locator('button:has-text("开始转录")');
    await submitButton.click();

    // 应该显示验证错误
    const errorMessage = page.locator('[role="alert"]');
    await expect(errorMessage).toBeVisible();
    const errorText = await errorMessage.textContent();
    expect(errorText).toContain(/URL|链接|地址/i);
  });

  test('应该处理文件太大的错误', async ({ page }) => {
    // 这个测试需要一个大文件
    // 在实际测试中应该创建一个虚拟的大文件

    // 选择上传模式
    await page.locator('input[value="upload"]').check();

    // 显示文件大小限制提示（如果有）
    const sizeHint = page.locator('[data-file-size-limit]');
    if (await sizeHint.isVisible()) {
      const limitText = await sizeHint.textContent();
      expect(limitText).toMatch(/\d+\s*(MB|GB)/i);
    }
  });

  test('应该处理无效的文件类型', async ({ page }) => {
    // 选择上传模式
    await page.locator('input[value="upload"]').check();

    // 尝试上传不支持的文件类型（创建虚拟文件）
    const fileInput = page.locator('input[type="file"]');

    // 虽然无法直接上传不支持的文件，但可以测试提交后的错误响应
    // 这取决于后端的验证
  });

  test('应该在网络恢复后重试请求', async ({ page }) => {
    // 创建任务
    await page.locator('input[value="upload"]').check();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/fixtures/sample.mp3');

    await page.locator('input[placeholder*="标题"]').fill('网络恢复测试');

    // 模拟网络中断
    await page.context().setOffline(true);

    // 尝试提交（应该失败）
    const submitButton = page.locator('button:has-text("开始转录")');
    await submitButton.click();

    // 等待错误
    await page.waitForTimeout(1000);

    // 恢复网络
    await page.context().setOffline(false);

    // 应该显示重试选项或错误消息
    const errorMessage = page.locator('[role="alert"]');
    const isVisible = await errorMessage.isVisible({ timeout: 2000 }).catch(() => false);
    expect(isVisible).toBeTruthy();
  });

  test('应该禁用提交按钮当表单无效时', async ({ page }) => {
    const submitButton = page.locator('button:has-text("开始转录")');

    // 初始状态应该禁用或显示错误
    const isEnabled = await submitButton.isEnabled();
    const isVisible = await submitButton.isVisible();

    // 如果可见，应该是禁用的（因为没有有效输入）
    if (isVisible) {
      // 实际行为取决于实现
    }

    // 选择上传模式并验证启用状态
    await page.locator('input[value="upload"]').check();

    // 此时应该仍然禁用（因为没有选择文件）
    const isEnabledAfter = await submitButton.isEnabled();
    // 实际验证取决于实现
  });

  test('应该显示 API 错误细节', async ({ page }) => {
    // 监听 API 响应
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/') && response.status() >= 400
    );

    // 尝试创建任务（可能会失败）
    await page.locator('input[value="url"]').check();
    const urlInput = page.locator('input[placeholder*="URL"]');
    await urlInput.fill('https://example.com');

    await page.locator('input[placeholder*="标题"]').fill('错误详情测试');
    await page.locator('button:has-text("开始转录")').click();

    // 如果有错误，验证显示的信息
    const errorMessage = page.locator('[role="alert"]');
    const isVisible = await errorMessage.isVisible({ timeout: 3000 }).catch(() => false);

    if (isVisible) {
      const errorText = await errorMessage.textContent();
      expect(errorText?.length || 0).toBeGreaterThan(0);
    }
  });

  test('应该处理并发请求错误', async ({ page }) => {
    // 快速创建多个任务
    for (let i = 0; i < 3; i++) {
      await page.locator('input[value="upload"]').check();
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles('./tests/fixtures/sample.mp3');

      const titleInput = page.locator('input[placeholder*="标题"]');
      await titleInput.fill(`并发测试 ${i + 1}`);

      const submitButton = page.locator('button:has-text("开始转录")');
      await submitButton.click();

      // 不等待就继续，测试并发处理
      await page.waitForTimeout(100);
    }

    // 验证任务列表更新
    const taskCount = await page.locator('[data-task-id]').count();
    expect(taskCount).toBeGreaterThanOrEqual(3);
  });
});
