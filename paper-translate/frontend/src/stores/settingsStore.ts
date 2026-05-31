import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { TranslationProvider } from '../types';

interface SettingsState {
  // Translation settings
  provider: TranslationProvider;
  apiKeys: Record<TranslationProvider, string>;
  sourceLang: string;
  targetLang: string;
  
  // Reader settings
  fontSize: number;
  lineHeight: number;
  layout: 'horizontal' | 'vertical';
  
  // Actions
  setProvider: (provider: TranslationProvider) => void;
  setApiKey: (provider: TranslationProvider, key: string) => void;
  setSourceLang: (lang: string) => void;
  setTargetLang: (lang: string) => void;
  setFontSize: (size: number) => void;
  setLineHeight: (height: number) => void;
  setLayout: (layout: 'horizontal' | 'vertical') => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      // Default values — use baidu for reliable translation in China
      provider: 'baidu',
      apiKeys: {
        baidu: '20221030001424938|Yomc1tbkC0U5DGDqgNrW',
        deepl: '',
        google: '',
        openai: '',
        deepseek: '',
      },
      sourceLang: 'en',
      targetLang: 'zh',
      fontSize: 16,
      lineHeight: 1.8,
      layout: 'horizontal',

      // Actions
      setProvider: (provider) => set({ provider }),
      setApiKey: (provider, key) =>
        set((state) => ({
          apiKeys: { ...state.apiKeys, [provider]: key },
        })),
      setSourceLang: (sourceLang) => set({ sourceLang }),
      setTargetLang: (targetLang) => set({ targetLang }),
      setFontSize: (fontSize) => set({ fontSize }),
      setLineHeight: (lineHeight) => set({ lineHeight }),
      setLayout: (layout) => set({ layout }),
    }),
    {
      name: 'paper-translate-settings',
      version: 3,
      // Migration: ensure apiKeys has all provider keys and provider is valid
      migrate: (persisted: any) => {
        const validProviders = ['google', 'baidu', 'deepl', 'openai', 'deepseek'];
        const state = persisted || {};

        // Fix invalid cached provider (e.g. removed 'suapi')
        if (!validProviders.includes(state.provider)) {
          state.provider = 'baidu';
        }

        // Ensure all providers have apiKeys entries
        const defaults = {
          baidu: '20221030001424938|Yomc1tbkC0U5DGDqgNrW',
          deepl: '',
          google: '',
          openai: '',
          deepseek: '',
        };
        state.apiKeys = { ...defaults, ...(state.apiKeys || {}) };

        // Force-inject baidu key if empty (for migration from v1/v2)
        if (!state.apiKeys.baidu) {
          state.apiKeys.baidu = '20221030001424938|Yomc1tbkC0U5DGDqgNrW';
        }

        return state;
      },
    }
  )
);
