import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Sparkles } from 'lucide-react';

interface SubmitSectionProps {
  sourceType: 'upload' | 'url';
  file: File | null;
  url: string;
  model: string;
  formats: string[];
  isSubmitting: boolean;
  onSubmit: () => void;
  isValid: boolean;
  validationError?: string;
}

export function SubmitSection({
  sourceType,
  file,
  url,
  model,
  formats,
  isSubmitting,
  onSubmit,
  isValid,
  validationError,
}: SubmitSectionProps) {
  const hasSource = sourceType === 'upload' ? !!file : !!url.trim();

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* 验证信息 */}
          {!hasSource && (
            <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded text-sm text-amber-800 dark:text-amber-200">
              ⚠️ 请选择{sourceType === 'upload' ? '文件' : 'URL'}
            </div>
          )}

          {!model && (
            <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded text-sm text-amber-800 dark:text-amber-200">
              ⚠️ 请选择 Whisper 模型
            </div>
          )}

          {formats.length === 0 && (
            <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded text-sm text-amber-800 dark:text-amber-200">
              ⚠️ 请选择至少一个输出格式
            </div>
          )}

          {validationError && (
            <div className="p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded text-sm text-red-800 dark:text-red-200">
              ❌ {validationError}
            </div>
          )}

          {/* 提交按钮 */}
          <Button
            onClick={onSubmit}
            disabled={!isValid || isSubmitting}
            size="lg"
            className="w-full"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="animate-spin mr-2" />
                创建中...
              </>
            ) : (
              <>
                <Sparkles size={18} className="mr-2" />
                创建转录任务
              </>
            )}
          </Button>

          <div className="text-xs text-gray-500 text-center">
            💡 创建后可在下方查看任务进度，支持 SSE 实时更新
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
