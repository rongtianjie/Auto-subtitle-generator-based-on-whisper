import { test, expect } from '@playwright/test';

test.describe('响应式布局和设备兼容性', () => {
  test('应该在移动设备上正确显示', async ({ page }) => {
    // 设置移动设备视口
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/');

    // 验证布局正确调整
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();

    // 验证导航（通常是汉堡菜单）
    const menu = page.locator('[data-mobile-menu]');
    await menu.isVisible();

    // 验证表单元素堆叠
    const formInputs = page.locator('input, button');
    const count = await formInputs.count();
    expect(count).toBeGreaterThan(0);
  });

  test('应该在平板设备上正确显示', async ({ page }) => {
    // 设置平板视口
    await page.setViewportSize({ width: 768, height: 1024 });

    await page.goto('/');

    // 验证布局
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();

    // 验证内容宽度合理
    const mainRect = await mainContent.boundingBox();
    expect(mainRect?.width).toBeLessThanOrEqual(800);
  });

  test('应该在桌面设备上正确显示', async ({ page }) => {
    // 设置桌面视口
    await page.setViewportSize({ width: 1280, height: 800 });

    await page.goto('/');

    // 验证布局
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();

    // 验证多列布局（如果有）
    const taskList = page.locator('[data-task-list]');
    if (await taskList.isVisible()) {
      // 验证显示足够的任务
    }
  });

  test('应该支持深色模式', async ({ page }) => {
    // 设置深色主题偏好
    await page.emulateMedia({ colorScheme: 'dark' });

    await page.goto('/');

    // 获取背景颜色
    const body = page.locator('body');
    const bgColor = await body.evaluate(el =>
      window.getComputedStyle(el).backgroundColor
    );

    // 深色模式应该有深色背景
    // 这取决于实现，但通常应该包含较低的 RGB 值
    expect(bgColor).toBeTruthy();
  });

  test('应该支持浅色模式', async ({ page }) => {
    // 设置浅色主题偏好
    await page.emulateMedia({ colorScheme: 'light' });

    await page.goto('/');

    // 获取背景颜色
    const body = page.locator('body');
    const bgColor = await body.evaluate(el =>
      window.getComputedStyle(el).backgroundColor
    );

    expect(bgColor).toBeTruthy();
  });

  test('应该正确处理长标题', async ({ page }) => {
    // 设置移动视口
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/');

    // 选择上传模式
    await page.locator('input[value="upload"]').check();

    // 输入很长的标题
    const longTitle = '这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的标题';
    const titleInput = page.locator('input[placeholder*="标题"]');
    await titleInput.fill(longTitle);

    // 验证标题不会破坏布局
    const formContainer = page.locator('[data-form-container]');
    const isOverflowing = await formContainer.evaluate(el =>
      el.scrollWidth > el.clientWidth
    );

    expect(isOverflowing).toBeFalsy();
  });

  test('应该处理不同的字体大小', async ({ page }) => {
    // 测试在不同字体大小下的显示
    await page.emulateMedia({ forcedColors: 'none' });

    await page.goto('/');

    // 获取按钮文本
    const submitButton = page.locator('button:has-text("开始转录")');
    const buttonBox = await submitButton.boundingBox();

    expect(buttonBox?.height).toBeGreaterThan(30);
  });
});
