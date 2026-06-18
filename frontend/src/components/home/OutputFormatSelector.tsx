import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';

const OUTPUT_FORMATS = [
  { value: 'txt', label: '纯文本', ext: '.txt', desc: '完整转写文本' },
  { value: 'srt', label: '原始字幕', ext: '.srt', desc: '依据音频语言生成' },
  { value: 'vtt', label: 'Web 字幕', ext: '.vtt', desc: '适用于网页播放器' },
];

const HOT_LANGUAGES = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: '英文' },
  { value: 'ja', label: '日语' },
];

const MORE_LANGUAGES = [
  { value: 'ko', label: '韩语' },
  { value: 'fr', label: '法语' },
  { value: 'de', label: '德语' },
  { value: 'es', label: '西班牙语' },
  { value: 'ru', label: '俄语' },
  { value: 'pt', label: '葡萄牙语' },
  { value: 'th', label: '泰语' },
  { value: 'vi', label: '越南语' },
  { value: 'ar', label: '阿拉伯语' },
  { value: 'it', label: '意大利语' },
  { value: 'nl', label: '荷兰语' },
  { value: 'pl', label: '波兰语' },
];

interface OutputFormatSelectorProps {
  formats: string[];
  onFormatsChange: (formats: string[]) => void;
  translateEnabled: boolean;
  onTranslateChange: (enabled: boolean) => void;
  selectedLanguages: string[];
  onLanguagesChange: (languages: string[]) => void;
}

export function OutputFormatSelector({
  formats,
  onFormatsChange,
  translateEnabled,
  onTranslateChange,
  selectedLanguages,
  onLanguagesChange,
}: OutputFormatSelectorProps) {
  const [moreExpanded, setMoreExpanded] = useState(false);

  const toggleFormat = (format: string) => {
    onFormatsChange(
      formats.includes(format)
        ? formats.filter((f) => f !== format)
        : [...formats, format]
    );
  };

  const toggleLanguage = (lang: string) => {
    onLanguagesChange(
      selectedLanguages.includes(lang)
        ? selectedLanguages.filter((l) => l !== lang)
        : [...selectedLanguages, lang]
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>输出格式和翻译</CardTitle>
        <CardDescription>选择输出文件格式和翻译语言</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 输出格式 */}
        <div>
          <label className="text-sm font-medium mb-3 block">输出格式</label>
          <div className="space-y-2">
            {OUTPUT_FORMATS.map((format) => (
              <label
                key={format.value}
                className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900"
              >
                <Checkbox
                  checked={formats.includes(format.value)}
                  onCheckedChange={() => toggleFormat(format.value)}
                />
                <div className="flex-1">
                  <div className="font-medium text-sm">
                    {format.label} <span className="text-gray-500">{format.ext}</span>
                  </div>
                  <div className="text-xs text-gray-500">{format.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* 翻译设置 */}
        <div className="border-t pt-4">
          <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900 mb-3">
            <Checkbox
              checked={translateEnabled}
              onCheckedChange={onTranslateChange}
            />
            <div className="flex-1">
              <div className="font-medium text-sm">启用字幕翻译</div>
              <div className="text-xs text-gray-500">生成原文和翻译的双语字幕</div>
            </div>
          </label>

          {translateEnabled && (
            <div>
              <label className="text-sm font-medium mb-2 block">翻译语言 (可多选)</label>

              {/* 热门语言 */}
              <div className="mb-3">
                <p className="text-xs text-gray-500 mb-2">热门</p>
                <div className="grid grid-cols-3 gap-2">
                  {HOT_LANGUAGES.map((lang) => (
                    <button
                      key={lang.value}
                      onClick={() => toggleLanguage(lang.value)}
                      className={`
                        p-2 rounded border text-sm transition-colors
                        ${selectedLanguages.includes(lang.value)
                          ? 'bg-blue-500 text-white border-blue-500'
                          : 'border-gray-300 dark:border-gray-600 hover:border-blue-300'
                        }
                      `}
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 更多语言 */}
              <div>
                <button
                  onClick={() => setMoreExpanded(!moreExpanded)}
                  className="flex items-center gap-2 text-sm text-blue-500 hover:text-blue-600 mb-2"
                >
                  {moreExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  {moreExpanded ? '隐藏' : '显示'}更多语言
                </button>

                {moreExpanded && (
                  <div className="grid grid-cols-3 gap-2 pt-2">
                    {MORE_LANGUAGES.map((lang) => (
                      <button
                        key={lang.value}
                        onClick={() => toggleLanguage(lang.value)}
                        className={`
                          p-2 rounded border text-sm transition-colors
                          ${selectedLanguages.includes(lang.value)
                            ? 'bg-blue-500 text-white border-blue-500'
                            : 'border-gray-300 dark:border-gray-600 hover:border-blue-300'
                          }
                        `}
                      >
                        {lang.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
