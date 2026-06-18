import { useEffect } from 'react';
import { taskApi } from '@/lib/api';
import { PageHeader } from '@/components/shared/PageHeader';
import { TaskSourceSelector } from '@/components/home/TaskSourceSelector';
import { ModelSelector } from '@/components/home/ModelSelector';
import { OutputFormatSelector } from '@/components/home/OutputFormatSelector';
import { SubmitSection } from '@/components/home/SubmitSection';
import { TaskList } from '@/components/home/TaskList';
import { useTaskForm } from '@/hooks/useTaskForm';
import { useAppContext } from '@/context/AppContext';

export default function Home() {
  const {
    sourceType,
    setSourceType,
    file,
    setFile,
    url,
    setUrl,
    title,
    setTitle,
    model,
    setModel,
    formats,
    setFormats,
    langs,
    setLangs,
    translateEnabled,
    setTranslateEnabled,
    isDragging,
    setIsDragging,
    isSubmitting,
    validationError,
    isValid: checkValid,
    submitTask,
  } = useTaskForm();

  const { recentTasks, setRecentTasks, isLoadingTasks, setIsLoadingTasks, showNotification } =
    useAppContext();

  // 加载最近任务
  useEffect(() => {
    loadRecentTasks();
  }, []);

  // 自动刷新：当有正在执行的任务时，每 3 秒刷新列表
  useEffect(() => {
    const hasRunning = recentTasks.some((t) => t.status === 'processing' || t.status === 'queued');
    if (!hasRunning) return;
    const interval = setInterval(loadRecentTasks, 3000);
    return () => clearInterval(interval);
  }, [recentTasks]);

  const loadRecentTasks = async () => {
    setIsLoadingTasks(true);
    try {
      const res = await taskApi.list({ page: 1, page_size: 5 });
      setRecentTasks(res.data.tasks);
    } catch {
      // 用户可能未登录，忽略错误
    } finally {
      setIsLoadingTasks(false);
    }
  };

  const handleSubmit = async () => {
    const task = await submitTask();
    if (task) {
      showNotification('success', '任务创建成功！');
      // 重新加载列表
      loadRecentTasks();
    } else if (validationError) {
      showNotification('error', validationError);
    }
  };

  const isFormValid = checkValid();

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <PageHeader title="转录任务" description="使用 Whisper AI 转录和翻译音视频" />

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：表单区域 */}
          <div className="lg:col-span-2 space-y-4">
            <TaskSourceSelector
              sourceType={sourceType}
              onSourceTypeChange={setSourceType}
              file={file}
              onFileChange={setFile}
              url={url}
              onUrlChange={setUrl}
              title={title}
              onTitleChange={setTitle}
              isDragging={isDragging}
              onDragChange={setIsDragging}
            />

            <ModelSelector selectedModel={model} onModelChange={setModel} />

            <OutputFormatSelector
              formats={formats}
              onFormatsChange={setFormats}
              translateEnabled={translateEnabled}
              onTranslateChange={setTranslateEnabled}
              selectedLanguages={langs}
              onLanguagesChange={setLangs}
            />

            <SubmitSection
              sourceType={sourceType}
              file={file}
              url={url}
              model={model}
              formats={formats}
              isSubmitting={isSubmitting}
              onSubmit={handleSubmit}
              isValid={isFormValid}
              validationError={validationError}
            />
          </div>

          {/* 右侧：任务列表 */}
          <div>
            <TaskList tasks={recentTasks} isLoading={isLoadingTasks} onRefresh={loadRecentTasks} />
          </div>
        </div>
      </div>
    </div>
  );
}
