import axios, { AxiosError } from 'axios';
import type {
  FileUploadResponse,
  TranslationRequest,
  TranslationResponse,
  TranslationResult,
  ApiError,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2分钟：上传大PDF + 后端PyMuPDF解析需要足够时间
});

// Error handler
const handleError = (error: AxiosError): never => {
  if (error.response?.data) {
    const data = error.response.data as any;
    // FastAPI returns errors as {"detail": {"error_code": "...", "message": "..."}}
    const detail = data?.detail;
    const message = typeof detail === 'object' && detail !== null
      ? (detail.message || JSON.stringify(detail))
      : (detail || data?.message || '请求失败');
    console.error('[API Error]', error.response.status, message, data);
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  console.error('[API Error]', error.message);
  throw new Error(error.message || '网络错误');
};

// PDF API
export const pdfApi = {
  upload: async (file: File): Promise<FileUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await api.post('/pdf/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getInfo: async (fileId: string) => {
    try {
      const response = await api.get(`/pdf/${fileId}/info`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  delete: async (fileId: string) => {
    try {
      const response = await api.delete(`/pdf/${fileId}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  /** Get the raw PDF URL for pdf.js rendering. */
  getServeUrl: (fileId: string) => {
    return `${API_BASE_URL}/pdf/${fileId}/serve`;
  },
};

// Translation API
export const translateApi = {
  start: async (request: TranslationRequest): Promise<TranslationResponse> => {
    try {
      const response = await api.post('/translate', request);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getStatus: async (taskId: string): Promise<TranslationResponse> => {
    try {
      const response = await api.get(`/translate/${taskId}/status`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getResult: async (taskId: string): Promise<TranslationResult> => {
    try {
      const response = await api.get(`/translate/${taskId}/result`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  cancel: async (taskId: string) => {
    try {
      const response = await api.post(`/translate/${taskId}/cancel`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  delete: async (taskId: string) => {
    try {
      const response = await api.delete(`/translate/${taskId}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  /** Get the export PDF download URL. */
  getExportPdfUrl: (taskId: string) => {
    return `${API_BASE_URL}/translate/${taskId}/export/pdf`;
  },
};

export default api;
