import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Download, BookOpen, Columns } from 'lucide-react';
import { ImmersiveReader } from '../components/reader/ImmersiveReader';
import { DualReader } from '../components/reader/DualReader';
import { Loading } from '../components/common/Loading';
import { translateApi } from '../services/api';
import { useSettingsStore } from '../stores/settingsStore';
import type { TranslationResult } from '../types';

export type ReaderMode = 'immersive' | 'dual';

export const Reader: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const [result, setResult] = useState<TranslationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [readerMode, setReaderMode] = useState<ReaderMode>('dual');
  const { fontSize, setFontSize } = useSettingsStore();

  useEffect(() => {
    const fetchResult = async () => {
      if (!taskId) {
        setError('没有可用的翻译任务 ID');
        setLoading(false);
        return;
      }

      try {
        const data = await translateApi.getResult(taskId);
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取翻译结果失败');
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [taskId]);

  const handleExportPDF = () => {
    if (!taskId) return;
    const url = translateApi.getExportPdfUrl(taskId);
    window.open(url, '_blank');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loading size="lg" text="加载翻译结果..." />
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <p className="text-red-600 mb-4">{error || '无法加载翻译结果'}</p>
        <Link
          to="/"
          className="text-primary-600 hover:text-primary-700 flex items-center"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          返回首页
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="flex items-center justify-between px-4 h-14">
          <div className="flex items-center space-x-4">
            <Link
              to="/"
              className="flex items-center text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="h-5 w-5 mr-1" />
              返回
            </Link>
            <h1 className="font-medium text-gray-900 truncate max-w-md">
              {result.filename}
            </h1>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">
              共 {result.page_count} 页
            </span>
          </div>
        </div>
      </header>

      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 sticky top-14 z-20">
        {/* Left: Reader mode toggle + font size */}
        <div className="flex items-center space-x-4">
          {/* Mode toggle */}
          <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => setReaderMode('dual')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                readerMode === 'dual'
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Columns className="h-4 w-4" />
              <span>双语对照</span>
            </button>
            <button
              onClick={() => setReaderMode('immersive')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                readerMode === 'immersive'
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <BookOpen className="h-4 w-4" />
              <span>沉浸阅读</span>
            </button>
          </div>

          {/* Font size */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">字号</span>
            <input
              type="range"
              min="8"
              max="18"
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value))}
              className="w-20"
            />
            <span className="text-sm text-gray-600 w-8">{fontSize}px</span>
          </div>
        </div>

        {/* Right: Export */}
        <button
          onClick={handleExportPDF}
          className="flex items-center space-x-1.5 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Download className="h-4 w-4" />
          <span>导出PDF</span>
        </button>
      </div>

      {/* Reader */}
      <main>
        {readerMode === 'dual' ? (
          <DualReader pages={result.pages} />
        ) : (
          <ImmersiveReader
            pdfFileId={result.file_id}
            pages={result.pages}
          />
        )}
      </main>
    </div>
  );
};
