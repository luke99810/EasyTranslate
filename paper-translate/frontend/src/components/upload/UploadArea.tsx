import React, { useCallback, useState } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import { Button } from '../common/Button';

interface UploadAreaProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  onClear: () => void;
  isUploading?: boolean;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

export const UploadArea: React.FC<UploadAreaProps> = ({
  onFileSelect,
  selectedFile,
  onClear,
  isUploading = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (file: File): boolean => {
    setError(null);

    // Check file type
    if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
      setError('请选择PDF格式文件');
      return false;
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      setError(`文件大小超过50MB限制`);
      return false;
    }

    return true;
  };

  const handleFileChange = (file: File | null) => {
    if (file && validateFile(file)) {
      onFileSelect(file);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileChange(files[0]);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileChange(files[0]);
    }
  };

  if (selectedFile) {
    return (
      <div className="w-full max-w-2xl mx-auto">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-primary-100 rounded-lg">
                <FileText className="h-8 w-8 text-primary-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={onClear}
              disabled={isUploading}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl p-12 text-center
          transition-all duration-200 ease-in-out
          ${isDragging 
            ? 'border-primary-500 bg-primary-50' 
            : 'border-gray-300 hover:border-gray-400 bg-white'
          }
        `}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleInputChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        <div className="space-y-4">
          <div className={`
            mx-auto w-16 h-16 rounded-full flex items-center justify-center
            ${isDragging ? 'bg-primary-100' : 'bg-gray-100'}
          `}>
            <Upload className={`
              h-8 w-8
              ${isDragging ? 'text-primary-600' : 'text-gray-400'}
            `} />
          </div>
          
          <div>
            <p className="text-lg font-medium text-gray-900">
              拖拽PDF文件到此处
            </p>
            <p className="text-sm text-gray-500 mt-1">
              或点击选择文件
            </p>
          </div>
          
          <p className="text-xs text-gray-400">
            支持 PDF 格式，最大 50MB
          </p>
        </div>
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-600 text-center">{error}</p>
      )}
    </div>
  );
};
