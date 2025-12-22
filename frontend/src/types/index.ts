export interface MoldSettings {
  wallThickness: number;
  maxWidth: number;
  maxHeight: number;
  maxDepth: number;
}

export interface PromptInfo {
  promptUsed: string;
  modelUsed: string;
}

export interface PromptTemplate {
  prompt: string;
  model: string;
}

export interface PromptTemplates {
  extractSubject: PromptTemplate;
  generateImage: PromptTemplate;
  createDepthMap: PromptTemplate;
  generateMold: PromptTemplate;
}

export interface ImageResult {
  image: string;
  promptInfo: PromptInfo;
}

export interface GenerationState {
  step: 'input' | 'processing' | 'customize' | 'error';
  inputType: 'image' | 'prompt' | null;
  originalImage: string | null;
  processedImage: string | null;
  depthMap: string | null;
  stlBlob: Blob | null;
  errorMessage: string | null;
  currentProcessingStep: string | null;
  currentPromptInfo: PromptInfo | null;
  extractionPromptInfo: PromptInfo | null;
  depthMapPromptInfo: PromptInfo | null;
}

export const DEFAULT_MOLD_SETTINGS: MoldSettings = {
  wallThickness: 5,
  maxWidth: 100,
  maxHeight: 100,
  maxDepth: 30,
};
