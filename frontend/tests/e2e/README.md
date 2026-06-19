# E2E 测试指南

## 概述

本项目使用 Playwright 进行端到端 (E2E) 测试，涵盖以下场景：

### 测试套件

1. **任务创建流程** (`task-creation.spec.ts`)
   - 上传音频文件创建任务
   - 从 YouTube URL 创建任务
   - 表单验证
   - 选择翻译语言
   - 多输出格式选择
   - 拖放文件上传

2. **任务监控流程** (`task-monitoring.spec.ts`)
   - 显示实时进度
   - 取消运行中的任务
   - 显示完成后的输出
   - 错误信息显示
   - 自动刷新列表
   - 排序验证

3. **错误处理和网络恢复** (`error-handling.spec.ts`)
   - API 超时处理
   - 无效 URL 验证
   - 文件大小限制
   - 文件类型验证
   - 网络恢复重试
   - 并发请求错误处理

4. **响应式布局** (`responsive.spec.ts`)
   - 移动设备兼容性
   - 平板设备兼容性
   - 桌面设备兼容性
   - 深色/浅色模式
   - 长内容处理

## 安装依赖

```bash
cd frontend
npm install
npm exec playwright install  # 安装浏览器驱动
```

## 运行测试

### 运行所有测试
```bash
npm run test:e2e
```

### 运行特定测试文件
```bash
npm run test:e2e -- tests/e2e/task-creation.spec.ts
```

### 运行特定测试
```bash
npm run test:e2e -- -g "应该能上传音频文件"
```

### UI 模式（推荐用于调试）
```bash
npm run test:e2e:ui
```

### 调试模式
```bash
npm run test:e2e:debug
```

## 环境配置

### 自定义后端地址
```bash
BASE_URL=http://localhost:8000 npm run test:e2e
```

### 指定浏览器
```bash
npm run test:e2e -- --project=chromium
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit
```

## 测试样本数据

### 生成测试音频文件
```bash
cd tests/fixtures
bash generate-samples.sh
```

### 所需的样本文件
- `sample.mp3` - 2 秒测试音频

## CI/CD 集成

### GitHub Actions 示例
```yaml
- name: Run E2E Tests
  run: npm run test:e2e -- --reporter=github
```

### GitLab CI 示例
```yaml
e2e_tests:
  script:
    - npm ci
    - npm run test:e2e
  artifacts:
    paths:
      - playwright-report/
```

## 辅助函数

### helpers.ts 中提供的工具函数

- `waitForTaskCompletion(page, taskId, maxWaitMs)` - 等待任务完成
- `uploadFile(page, filePath)` - 上传文件
- `getTaskOutputs(page, taskId)` - 获取任务输出
- `getValidationErrors(page)` - 获取验证错误
- `waitForApiResponse(page, urlPattern)` - 等待 API 响应
- `slowDownNetwork(page)` - 模拟网络延迟
- `goOffline(page)` / `goOnline(page)` - 模拟离线/在线

## 故障排除

### 测试超时
- 增加 `maxWaitMs` 参数
- 检查后端服务是否运行
- 查看浏览器控制台错误

### 选择器失败
- 使用 UI 模式 (`npm run test:e2e:ui`) 调试选择器
- 检查 HTML 属性 `data-*` 是否存在
- 使用 `page.pause()` 暂停执行

### 文件上传问题
- 确保测试样本文件存在
- 检查文件路径是否相对于项目根目录
- 验证 input[type="file"] 选择器正确

## 最佳实践

1. **使用 data 属性定位元素**
   ```html
   <button data-test-id="submit">提交</button>
   ```
   ```typescript
   await page.locator('[data-test-id="submit"]').click();
   ```

2. **等待网络完成**
   ```typescript
   await page.waitForLoadState('networkidle');
   ```

3. **避免硬等待**
   ```typescript
   // ❌ 不好
   await page.waitForTimeout(5000);
   
   // ✅ 好
   await page.locator('[data-task-id]').first().waitFor();
   ```

4. **使用事件监听器**
   ```typescript
   const responsePromise = page.waitForResponse(/\/api\/tasks/);
   await page.locator('button').click();
   await responsePromise;
   ```

5. **记录调试信息**
   ```typescript
   test.beforeEach(async ({ page }) => {
     page.on('console', msg => console.log(msg.text()));
   });
   ```

## 性能基准

预期的测试执行时间：
- 单个测试: 5-10 秒
- 全套测试: 3-5 分钟（并行）
- 包含视频录制: +50%

## 覆盖范围

当前测试覆盖以下用户流程：

| 功能 | 单位测试 | E2E 测试 | 覆盖率 |
|------|---------|---------|--------|
| 任务创建 (上传) | ✓ | ✓ | 100% |
| 任务创建 (URL) | ✓ | ✓ | 100% |
| 任务监控 | ✓ | ✓ | 95% |
| 任务取消 | ✓ | ✓ | 90% |
| 输出下载 | ✓ | ✓ | 85% |
| 错误处理 | ✓ | ✓ | 85% |
| 响应式设计 | - | ✓ | 80% |

## 维护和更新

### 添加新测试
1. 创建新的 `.spec.ts` 文件
2. 使用现有的 `test.describe()` 和 `test()` 模式
3. 导入和使用 `helpers.ts` 中的工具函数
4. 运行测试验证
5. 提交 PR 进行代码审查

### 更新选择器
当 UI 变化时，需要更新对应的选择器：
1. 使用 UI 模式找到新选择器
2. 更新所有受影响的测试
3. 运行测试确保通过

## 相关文档

- [Playwright 官方文档](https://playwright.dev/)
- [项目文档](../../OPTIMIZATION_FRONTEND.md)
- [API 文档](../../OPTIMIZATION_API.md)
