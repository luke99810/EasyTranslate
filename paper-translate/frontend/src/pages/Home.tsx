import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Shield, Languages, Zap, Github, ChevronRight } from 'lucide-react';
import { UploadArea } from '../components/upload/UploadArea';
import { TranslationSettings } from '../components/settings/TranslationSettings';
import { Button } from '../components/common/Button';
import { Loading } from '../components/common/Loading';
import { ProgressBar } from '../components/common/ProgressBar';
import { pdfApi, translateApi } from '../services/api';
import { useTranslationStore } from '../stores/translationStore';
import { useSettingsStore } from '../stores/settingsStore';

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  
  const {
    uploadedFile,
    isUploading,
    uploadError,
    translationTask,
    isTranslating,
    translationError,
    setUploadedFile,
    setIsUploading,
    setUploadError,
    setTranslationTask,
    setIsTranslating,
    setTranslationError,
    updateTranslationStatus,
    setPollInterval,
    pollInterval,
    reset,
  } = useTranslationStore();

  const { provider, apiKeys, sourceLang, targetLang } = useSettingsStore();

  // Poll translation status
  useEffect(() => {
    if (translationTask?.task_id && isTranslating) {
      const interval = window.setInterval(async () => {
        try {
          const status = await translateApi.getStatus(translationTask.task_id);
          
          updateTranslationStatus(
            status.status,
            status.progress,
            status.message
          );

          if (status.status === 'completed' || status.status === 'failed') {
            if (pollInterval) {
              clearInterval(pollInterval);
              setPollInterval(null);
            }
            setIsTranslating(false);
          }
        } catch (error) {
          console.error('Failed to get status:', error);
        }
      }, 2000);

      setPollInterval(interval);

      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [translationTask?.task_id, isTranslating]);

  const handleFileSelect = async (file: File) => {
    setSelectedFile(file);
    setUploadError(null);
  };

  const handleClear = () => {
    setSelectedFile(null);
    reset();
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      // Step 1: Upload file (fast — only saves to disk)
      const response = await pdfApi.upload(selectedFile);
      setUploadedFile(response);

      // Step 2: Parse PDF to get page count (may be slow for large PDFs)
      try {
        const info = await pdfApi.getInfo(response.file_id);
        setUploadedFile({
          ...response,
          page_count: info.page_count,
        });
      } catch (infoError) {
        // Info fetch failed — file is still uploaded, page count just unknown
        console.warn('Failed to fetch PDF info after upload:', infoError);
        setUploadError(
          infoError instanceof Error ? infoError.message : 'PDF解析失败，但文件已上传'
        );
      }
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : '上传失败');
    } finally {
      setIsUploading(false);
    }
  };

  const handleTranslate = async () => {
    if (!uploadedFile) return;

    // Check if selected provider needs API key
    const needsKey = ['deepl', 'openai', 'baidu'].includes(provider);
    if (needsKey && !apiKeys[provider]) {
      const nameMap: Record<string, string> = { deepl: 'DeepL', openai: 'OpenAI', deepseek: 'DeepSeek', baidu: '百度翻译' };
      setTranslationError(`请先在设置中配置${nameMap[provider] || provider} API Key`);
      setShowSettings(true);
      return;
    }

    setIsTranslating(true);
    setTranslationError(null);

    try {
      const response = await translateApi.start({
        file_id: uploadedFile.file_id,
        provider,
        api_key: apiKeys[provider] || undefined,
        source_lang: sourceLang,
        target_lang: targetLang,
      });
      setTranslationTask(response);
    } catch (error) {
      setTranslationError(error instanceof Error ? error.message : '翻译启动失败');
      setIsTranslating(false);
    }
  };

  const handleViewResult = () => {
    if (translationTask?.task_id) {
      navigate(`/reader/${translationTask.task_id}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <FileText className="h-8 w-8 text-primary-600" />
              <span className="text-xl font-bold text-gray-900">PaperTranslate</span>
            </div>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-gray-700"
            >
              <Github className="h-6 w-6" />
            </a>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            学术PDF翻译工具
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            免费开源，公式保留，排版不乱，双语对照阅读
          </p>

          {/* Upload Area */}
          <div className="mb-8">
            <UploadArea
              onFileSelect={handleFileSelect}
              selectedFile={selectedFile}
              onClear={handleClear}
              isUploading={isUploading}
            />
          </div>

          {/* Error Messages */}
          {uploadError && (
            <p className="mb-4 text-red-600">{uploadError}</p>
          )}
          {translationError && (
            <p className="mb-4 text-red-600">{translationError}</p>
          )}

          {/* Action Buttons */}
          {selectedFile && !uploadedFile && (
            <div className="flex justify-center space-x-4 mb-8">
              <Button
                onClick={handleUpload}
                isLoading={isUploading}
                size="lg"
              >
                上传文件
              </Button>
              <Button
                variant="secondary"
                onClick={() => setShowSettings(!showSettings)}
                size="lg"
              >
                翻译设置
              </Button>
            </div>
          )}

          {/* Settings Panel */}
          {showSettings && (
            <div className="card p-6 mb-8 max-w-2xl mx-auto text-left">
              <TranslationSettings />
            </div>
          )}

          {/* Translation Progress */}
          {uploadedFile && (
            <div className="card p-6 mb-8 max-w-2xl mx-auto">
              <div className="flex items-center justify-between mb-4">
                <div className="text-left">
                  <p className="font-medium text-gray-900">{uploadedFile.filename}</p>
                  <p className="text-sm text-gray-500">{uploadedFile.page_count} 页</p>
                </div>
                {translationTask?.status === 'completed' ? (
                  <Button onClick={handleViewResult}>
                    查看结果 <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    onClick={handleTranslate}
                    isLoading={isTranslating}
                    disabled={isTranslating || translationTask?.status === 'processing'}
                  >
                    {isTranslating ? '翻译中...' : '开始翻译'}
                  </Button>
                )}
              </div>

              {translationTask && (
                <ProgressBar
                  progress={translationTask.progress}
                  message={translationTask.message}
                />
              )}
            </div>
          )}
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-center text-gray-900 mb-12">
            核心功能
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">本地处理</h3>
              <p className="text-gray-600">文件在本地处理，不上传云端，保护您的论文隐私</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Zap className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">公式保留</h3>
              <p className="text-gray-600">智能识别并保留LaTeX公式，翻译后公式不乱码</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Languages className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">双语对照</h3>
              <p className="text-gray-600">原文译文并排显示，支持同步滚动，阅读更高效</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-50 border-t border-gray-200 py-8">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="text-gray-500 text-sm">
            PaperTranslate - 免费开源的学术PDF翻译工具
          </p>
          <p className="text-gray-400 text-xs mt-2">
            文件仅在本地处理，不会上传到服务器
          </p>
        </div>
      </footer>
    </div>
  );
};
