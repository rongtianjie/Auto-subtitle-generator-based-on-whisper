import { useState, useCallback } from 'react';
import { taskApi } from '@/lib/api';
import type { Task } from '@/types';

export function useTaskForm() {
  const [sourceType, setSourceType] = useState<'upload' | 'url'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [model, setModel] = useState('base');
  const [formats, setFormats] = useState<string[]>(['txt', 'srt', 'vtt']);
  const [langs, setLangs] = useState<string[]>(['zh']);
  const [translateEnabled, setTranslateEnabled] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const isValid = useCallback(() => {
    setValidationError(null);

    if (sourceType === 'upload' && !file) {
      setValidationError('请选择要上传的文件');
      return false;
    }

    if (sourceType === 'url' && !url.trim()) {
      setValidationError('请输入视频链接');
      return false;
    }

    if (!model) {
      setValidationError('请选择 Whisper 模型');
      return false;
    }

    if (formats.length === 0) {
      setValidationError('请选择至少一个输出格式');
      return false;
    }

    if (translateEnabled && langs.length === 0) {
      setValidationError('请选择至少一个翻译语言');
      return false;
    }

    return true;
  }, [sourceType, file, url, model, formats, translateEnabled, langs]);

  const submitTask = useCallback(async (): Promise<Task | null> => {
    if (!isValid()) {
      return null;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('source_type', sourceType);
      formData.append('title', title || (sourceType === 'upload' ? file?.name : 'URL 视频'));
      formData.append('whisper_model', model);
      formData.append('output_formats', JSON.stringify(formats));

      if (sourceType === 'upload' && file) {
        formData.append('file', file);
      } else if (sourceType === 'url') {
        formData.append('source_url', url);
      }

      if (translateEnabled) {
        formData.append('translate_target_langs', JSON.stringify(langs));
      }

      const response = await taskApi.create(formData);

      // 重置表单
      setFile(null);
      setUrl('');
      setTitle('');
      setFormats(['txt', 'srt', 'vtt']);
      setLangs(['zh']);
      setValidationError(null);

      return response.data;
    } catch (error: any) {
      const message = error.userMessage || error.response?.data?.message || '创建任务失败，请重试';
      setValidationError(message);
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, [isValid, sourceType, file, url, title, model, formats, langs, translateEnabled]);

  return {
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
    isValid,
    submitTask,
  };
}
