import React from 'react';
import { useSettingsStore } from '../../stores/settingsStore';
import type { TranslationProvider } from '../../types';

const PROVIDERS: { value: TranslationProvider; label: string; description: string; needsApiKey: boolean; keyPlaceholder?: string }[] = [
  {
    value: 'google',
    label: '免费翻译（MyMemory）',
    description: '免费，无需API Key，国内可用，适合快速体验',
    needsApiKey: false,
  },
  {
    value: 'baidu',
    label: '百度翻译',
    description: '学术翻译效果较好，需要百度翻译API Key',
    needsApiKey: true,
    keyPlaceholder: 'APP_ID|Secret_Key（用竖线分隔）',
  },
  {
    value: 'deepseek',
    label: 'DeepSeek',
    description: 'AI学术翻译，上下文理解强，性价比高，推荐使用',
    needsApiKey: true,
    keyPlaceholder: 'sk-xxx（DeepSeek API Key）',
  },
  {
    value: 'openai',
    label: 'OpenAI',
    description: 'AI学术翻译，上下文理解强，翻译质量最佳',
    needsApiKey: true,
    keyPlaceholder: 'sk-xxx（OpenAI API Key）',
  },
  {
    value: 'deepl',
    label: 'DeepL 翻译',
    description: '翻译质量最佳，学术文献推荐，需要API Key',
    needsApiKey: true,
    keyPlaceholder: 'DeepL API Key',
  },
];

const LANGUAGES = [
  { code: 'en', label: '英语' },
  { code: 'zh', label: '中文' },
  { code: 'ja', label: '日语' },
  { code: 'ko', label: '韩语' },
  { code: 'de', label: '德语' },
  { code: 'fr', label: '法语' },
  { code: 'es', label: '西班牙语' },
  { code: 'ru', label: '俄语' },
];

export const TranslationSettings: React.FC = () => {
  const {
    provider,
    apiKeys,
    sourceLang,
    targetLang,
    setProvider,
    setApiKey,
    setSourceLang,
    setTargetLang,
  } = useSettingsStore();

  const currentProvider = PROVIDERS.find(p => p.value === provider);
  const needsApiKey = currentProvider?.needsApiKey ?? false;

  return (
    <div className="space-y-6">
      {/* Provider Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          翻译引擎
        </label>
        <div className="space-y-3">
          {PROVIDERS.map((p) => (
            <label
              key={p.value}
              className={`
                flex items-start p-4 border rounded-lg cursor-pointer transition-colors
                ${provider === p.value
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
                }
              `}
            >
              <input
                type="radio"
                name="provider"
                value={p.value}
                checked={provider === p.value}
                onChange={(e) => setProvider(e.target.value as TranslationProvider)}
                className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500"
              />
              <div className="ml-3">
                <span className="block font-medium text-gray-900">{p.label}</span>
                <span className="block text-sm text-gray-500">{p.description}</span>
                {p.needsApiKey && (
                  <span className="block text-xs text-amber-600 mt-1">
                    ⚠ 需要配置 API Key
                  </span>
                )}
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* API Key Input */}
      {needsApiKey && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            API Key
            {provider === 'deepl' && (
              <a
                href="https://www.deepl.com/pro-api"
                target="_blank"
                rel="noopener noreferrer"
                className="ml-2 text-primary-600 hover:text-primary-700 text-xs"
              >
                (获取 DeepL API Key →)
              </a>
            )}
            {provider === 'openai' && (
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="ml-2 text-primary-600 hover:text-primary-700 text-xs"
              >
                (获取 OpenAI API Key →)
              </a>
            )}
          </label>
          <input
            type="password"
            value={apiKeys[provider] || ''}
            onChange={(e) => setApiKey(provider, e.target.value)}
            placeholder={currentProvider?.keyPlaceholder || `输入${currentProvider?.label} API Key`}
            className="input"
          />
          <p className="mt-1 text-xs text-gray-500">
            API Key 仅存储在本地浏览器中，不会上传到服务器
          </p>
          {provider === 'openai' && (
            <p className="mt-1 text-xs text-blue-600">
              💡 前往{' '}
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700"
              >
                OpenAI 控制台
              </a>
              {' '}获取 API Key
            </p>
          )}
          {provider === 'deepseek' && (
            <p className="mt-1 text-xs text-blue-600">
              💡 前往{' '}
              <a
                href="https://platform.deepseek.com/api_keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700"
              >
                DeepSeek 控制台
              </a>
              {' '}获取 API Key
            </p>
          )}
          {provider === 'baidu' && (
            <p className="mt-1 text-xs text-blue-600">
              💡 格式为 APP_ID|Secret_Key，用竖线分隔，{' '}
              <a
                href="https://fanyi-api.baidu.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700"
              >
                前往百度翻译开放平台获取 →
              </a>
            </p>
          )}
        </div>
      )}

      {/* Language Selection */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            源语言
          </label>
          <select
            value={sourceLang}
            onChange={(e) => setSourceLang(e.target.value)}
            className="input"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            目标语言
          </label>
          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            className="input"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};
