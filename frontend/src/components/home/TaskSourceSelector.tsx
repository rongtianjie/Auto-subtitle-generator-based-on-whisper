import React, { useRef, useState } from 'react';
import { Upload, Link as LinkIcon } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface TaskSourceSelectorProps {
  sourceType: 'upload' | 'url';
  onSourceTypeChange: (type: 'upload' | 'url') => void;
  file: File | null;
  onFileChange: (file: File | null) => void;
  url: string;
  onUrlChange: (url: string) => void;
  title: string;
  onTitleChange: (title: string) => void;
  isDragging: boolean;
  onDragChange: (dragging: boolean) => void;
}

export function TaskSourceSelector({
  sourceType,
  onSourceTypeChange,
  file,
  onFileChange,
  url,
  onUrlChange,
  title,
  onTitleChange,
  isDragging,
  onDragChange,
}: TaskSourceSelectorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (selectedFile: File | null) => {
    if (selectedFile && (selectedFile.type.startsWith('audio/') || selectedFile.type.startsWith('video/'))) {
      onFileChange(selectedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    onDragChange(true);
  };

  const handleDragLeave = () => {
    onDragChange(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    onDragChange(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>选择来源</CardTitle>
        <CardDescription>上传本地文件或提供在线视频链接</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={sourceType} onValueChange={(v) => onSourceTypeChange(v as 'upload' | 'url')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload size={18} />
              上传文件
            </TabsTrigger>
            <TabsTrigger value="url" className="flex items-center gap-2">
              <LinkIcon size={18} />
              视频链接
            </TabsTrigger>
          </TabsList>

          {/* 上传标签 */}
          <TabsContent value="upload" className="space-y-4">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                transition-colors
                ${isDragging ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' : 'border-gray-300 dark:border-gray-600'}
                ${file ? 'bg-green-50 dark:bg-green-950 border-green-300' : ''}
              `}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,video/*"
                className="hidden"
                onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
              />
              <Upload className="mx-auto mb-3 text-gray-400" size={32} />
              <p className="text-sm font-medium">点击选择或拖拽文件到此</p>
              <p className="text-xs text-gray-500 mt-1">支持 MP3、MP4、WAV、WebM 等格式，最大 2GB</p>
              {file && <p className="text-xs text-green-600 mt-2 font-semibold">✓ {file.name}</p>}
            </div>

            {file && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onFileChange(null)}
                className="w-full"
              >
                清除选择
              </Button>
            )}
          </TabsContent>

          {/* URL 标签 */}
          <TabsContent value="url" className="space-y-4">
            <Input
              placeholder="输入视频链接 (YouTube, 抖音, etc.)"
              value={url}
              onChange={(e) => onUrlChange(e.target.value)}
              className="w-full"
            />
            <p className="text-xs text-gray-500">支持 YouTube、抖音、B站等主流视频平台</p>
          </TabsContent>
        </Tabs>

        {/* 任务标题 */}
        <div className="mt-4">
          <label className="text-sm font-medium">任务标题 (可选)</label>
          <Input
            placeholder={file?.name || 'my-video'}
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            className="mt-2"
          />
        </div>
      </CardContent>
    </Card>
  );
}
