import React from 'react';
import { Download, Settings } from 'lucide-react';
import { useSettingsStore } from '../../stores/settingsStore';

interface ToolbarProps {
  onExportPDF?: () => void;
  onOpenSettings?: () => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  onExportPDF,
  onOpenSettings,
}) => {
  const { fontSize, setFontSize } = useSettingsStore();

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 sticky top-14 z-20">
      {/* Left: Font size control */}
      <div className="flex items-center space-x-3">
        <span className="text-sm text-gray-500">译文字号</span>
        <input
          type="range"
          min="8"
          max="18"
          value={fontSize}
          onChange={(e) => setFontSize(Number(e.target.value))}
          className="w-24"
        />
        <span className="text-sm text-gray-600 w-8">{fontSize}px</span>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center space-x-2">
        <button
          onClick={onExportPDF}
          className="flex items-center space-x-1 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Download className="h-4 w-4" />
          <span>导出PDF</span>
        </button>
        <button
          onClick={onOpenSettings}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
          title="设置"
        >
          <Settings className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
};
