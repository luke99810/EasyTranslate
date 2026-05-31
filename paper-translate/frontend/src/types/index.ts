export interface FileUploadResponse {
  file_id: string;
  filename: string;
  page_count: number;
  file_size: number;
  status: string;
}

export type TranslationProvider = 'google' | 'baidu' | 'deepl' | 'openai' | 'deepseek';

export interface TranslationRequest {
  file_id: string;
  provider: TranslationProvider;
  api_key?: string;
  source_lang: string;
  target_lang: string;
}

export type TranslationStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface TranslationResponse {
  task_id: string;
  status: TranslationStatus;
  progress: number;
  message: string;
  result?: {
    file_id: string;
    filename: string;
    page_count: number;
  };
}

export interface TextBlock {
  text: string;
  bbox: [number, number, number, number];
  font_size: number;
  font_name?: string;
  is_bold: boolean;
  is_italic: boolean;
  block_type: 'text' | 'formula';
}

export interface Formula {
  content: string;
  position: [number, number];
}

export interface PageContent {
  page_number: number;
  text_blocks: TextBlock[];
  translated_blocks: TextBlock[];
  formulas: Formula[];
}

export interface TranslationResult {
  file_id: string;
  filename: string;
  page_count: number;
  pages: PageContent[];
}

export interface ApiError {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
}
