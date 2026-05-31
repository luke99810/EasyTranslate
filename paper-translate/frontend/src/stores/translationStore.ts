import { create } from 'zustand';
import type { 
  FileUploadResponse, 
  TranslationResponse, 
  TranslationResult,
  TranslationStatus 
} from '../types';

interface TranslationState {
  // Upload state
  uploadedFile: FileUploadResponse | null;
  isUploading: boolean;
  uploadError: string | null;

  // Translation state
  translationTask: TranslationResponse | null;
  isTranslating: boolean;
  translationError: string | null;
  pollInterval: number | null;

  // Result state
  translationResult: TranslationResult | null;

  // Actions
  setUploadedFile: (file: FileUploadResponse | null) => void;
  setIsUploading: (isUploading: boolean) => void;
  setUploadError: (error: string | null) => void;

  setTranslationTask: (task: TranslationResponse | null) => void;
  setIsTranslating: (isTranslating: boolean) => void;
  setTranslationError: (error: string | null) => void;
  updateTranslationStatus: (status: TranslationStatus, progress: number, message: string) => void;
  setPollInterval: (interval: number | null) => void;

  setTranslationResult: (result: TranslationResult | null) => void;

  reset: () => void;
}

export const useTranslationStore = create<TranslationState>((set) => ({
  // Initial state
  uploadedFile: null,
  isUploading: false,
  uploadError: null,

  translationTask: null,
  isTranslating: false,
  translationError: null,
  pollInterval: null,

  translationResult: null,

  // Actions
  setUploadedFile: (uploadedFile) => set({ uploadedFile }),
  setIsUploading: (isUploading) => set({ isUploading }),
  setUploadError: (uploadError) => set({ uploadError }),

  setTranslationTask: (translationTask) => set({ translationTask }),
  setIsTranslating: (isTranslating) => set({ isTranslating }),
  setTranslationError: (translationError) => set({ translationError }),
  
  updateTranslationStatus: (status, progress, message) =>
    set((state) => ({
      translationTask: state.translationTask
        ? { ...state.translationTask, status, progress, message }
        : null,
    })),
  
  setPollInterval: (pollInterval) => set({ pollInterval }),

  setTranslationResult: (translationResult) => set({ translationResult }),

  reset: () =>
    set({
      uploadedFile: null,
      isUploading: false,
      uploadError: null,
      translationTask: null,
      isTranslating: false,
      translationError: null,
      pollInterval: null,
      translationResult: null,
    }),
}));
