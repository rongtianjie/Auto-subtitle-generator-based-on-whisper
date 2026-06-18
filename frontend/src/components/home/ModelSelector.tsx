import React, { useEffect, useState } from 'react';
import { Loader2, Download } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { modelApi } from '@/lib/api';

interface Model {
  value: string;
  label: string;
  desc: string;
  speed: number;
}

const MODELS: Model[] = [
  { value: 'tiny', label: 'Tiny', desc: '最快, 准确度最低', speed: 5 },
  { value: 'base', label: 'Base', desc: '快速', speed: 4 },
  { value: 'small', label: 'Small', desc: '推荐', speed: 3 },
  { value: 'medium', label: 'Medium', desc: '较慢, 更准确', speed: 2 },
  { value: 'large', label: 'Large', desc: '最慢, 最准确', speed: 1 },
];

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
}

export function ModelSelector({ selectedModel, onModelChange }: ModelSelectorProps) {
  const [modelStatus, setModelStatus] = useState<Record<string, boolean>>({});
  const [downloadingModel, setDownloadingModel] = useState<string | null>(null);

  useEffect(() => {
    modelApi
      .list()
      .then((res) => {
        const status: Record<string, boolean> = {};
        res.data.models.forEach((m: any) => {
          status[m.name] = m.is_downloaded;
        });
        setModelStatus(status);
      })
      .catch(() => {});
  }, []);

  const handleDownloadModel = async (modelName: string) => {
    setDownloadingModel(modelName);
    try {
      await modelApi.download(modelName);
      setModelStatus((prev) => ({ ...prev, [modelName]: true }));
    } catch (error) {
      console.error('Failed to download model:', error);
    } finally {
      setDownloadingModel(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Whisper 模型</CardTitle>
        <CardDescription>选择转录模型 (需提前下载)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-2">
          {MODELS.map((model) => {
            const isDownloaded = modelStatus[model.value] === true;
            const isDownloading = downloadingModel === model.value;

            return (
              <div
                key={model.value}
                className={`
                  p-3 border rounded-lg cursor-pointer transition-colors
                  ${selectedModel === model.value ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' : 'border-gray-200 dark:border-gray-700'}
                `}
                onClick={() => isDownloaded && onModelChange(model.value)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{model.label}</span>
                      <Badge variant={model.value === 'small' ? 'default' : 'secondary'}>
                        {model.desc}
                      </Badge>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {'█'.repeat(model.speed)}{'░'.repeat(5 - model.speed)} 速度: {model.speed}/5
                    </div>
                  </div>

                  {!isDownloaded ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDownloadModel(model.value);
                      }}
                      disabled={isDownloading}
                    >
                      {isDownloading ? (
                        <>
                          <Loader2 size={16} className="animate-spin mr-1" />
                          下载中
                        </>
                      ) : (
                        <>
                          <Download size={16} className="mr-1" />
                          下载
                        </>
                      )}
                    </Button>
                  ) : (
                    <Badge variant="outline" className="bg-green-50 dark:bg-green-950 border-green-300">
                      ✓ 已安装
                    </Badge>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 p-3 rounded">
          💡 提示：首次使用需要下载模型 (100MB-3GB)，仅需一次
        </div>
      </CardContent>
    </Card>
  );
}
