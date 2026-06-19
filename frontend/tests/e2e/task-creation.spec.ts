import { test, expect } from '@playwright/test';

test.describe('任务创建流程', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Subtitle Generator/i);
  });

  test('应该能上传音频文件并创建任务', async ({ page }) => {
    // 选择上传模式
    await page.locator('input[value="upload"]').check();

    // 上传文件
    const fileInput = page.locator('input[type="file"]');
    const testAudioPath = './tests/fixtures/sample.mp3';
    await fileInput.setInputFiles(testAudioPath);

    // 填写标题
    await page.locator('input[placeholder*="标题"]').fill('测试任务');

    // 选择模型
    await page.locator('[data-select="model"]').click();
    await page.locator('text=base').click();

    // 选择输出格式
    await page.locator('input[value="srt"]').check();
    await page.locator('input[value="vtt"]').check();

    // 提交表单
    const submitButton = page.locator('button:has-text("开始转录")');
    await submitButton.click();

    // 验证任务已创建
    const taskItem = page.locator('[data-task-id]').first();
    await expect(taskItem).toBeVisible();

    const taskStatus = await taskItem.locator('[data-status]').getAttribute('data-status');
    expect(['pending', 'queued']).toContain(taskStatus);
  });

  test('应该能从 YouTube URL 创建任务', async ({ page }) => {
    // 选择 URL 模式
    await page.locator('input[value="url"]').check();

    // 输入 URL
    const urlInput = page.locator('input[placeholder*="URL"]');
    await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

    // 填写标题
    await page.locator('input[placeholder*="标题"]').fill('YouTube 测试');

    // 选择输出格式
    await page.locator('input[value="txt"]').check();

    // 提交表单
    const submitButton = page.locator('button:has-text("开始转录")');
    await submitButton.click();

    // 验证任务已创建
    const taskItem = page.locator('[data-task-id]').first();
    await expect(taskItem).toBeVisible();
  });

  test('应该显示验证错误', async ({ page }) => {
    // 尝试在没有选择模式的情况下提交
    const submitButton = page.locator('button:has-text("开始转录")');
    await submitButton.click();

    // 应该显示验证错误
    const errorMessage = page.locator('[role="alert"]');
    await expect(errorMessage).toBeVisible();
  });

  test('应该能选择翻译语言', async ({ page }) => {
    // 选择上传模式
    await page.locator('input[value="upload"]').check();

    // 启用翻译
    const translateToggle = page.locator('input[type="checkbox"][aria-label*="翻译"]');
    await translateToggle.check();

    // 点击语言选择
    const languageSelect = page.locator('[data-select="languages"]');
    await languageSelect.click();

    // 选择中文
    await page.locator('text="中文"').click();

    // 验证语言已选中
    const selectedLanguage = page.locator('[data-selected-languages]');
    await expect(selectedLanguage).toContainText('中文');
  });

  test('应该能选择多个输出格式', async ({ page }) => {
    // 选择上传模式
    await page.locator('input[value="upload"]').check();

    // 验证格式复选框
    const txtCheckbox = page.locator('input[value="txt"]');
    const srtCheckbox = page.locator('input[value="srt"]');
    const vttCheckbox = page.locator('input[value="vtt"]');

    await expect(txtCheckbox).toBeChecked();
    await expect(srtCheckbox).toBeChecked();
    await expect(vttCheckbox).toBeChecked();

    // 取消选中一个格式
    await txtCheckbox.uncheck();
    await expect(txtCheckbox).not.toBeChecked();
  });

  test('拖放上传文件', async ({ page }) => {
    // 选择上传模式
    await page.locator('input[value="upload"]').check();

    // 模拟拖放
    const testAudioPath = './tests/fixtures/sample.mp3';
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testAudioPath);

    // 验证文件已上传
    await page.waitForTimeout(500);
    const fileName = page.locator('[data-filename]');
    await expect(fileName).toBeVisible();
  });
});
