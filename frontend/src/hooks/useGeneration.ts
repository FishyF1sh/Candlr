import { useReducer, useCallback, useEffect, useRef } from 'react';
import type { GenerationState, MoldSettings, PromptInfo, PromptTemplates } from '../types';
import { DEFAULT_MOLD_SETTINGS } from '../types';
import * as api from '../api/client';

type Action =
  | { type: 'START_IMAGE_PROCESSING'; image: string; promptInfo: PromptInfo }
  | { type: 'START_PROMPT_PROCESSING'; userPrompt: string; promptInfo: PromptInfo }
  | { type: 'SET_PROCESSING_STEP'; step: string; promptInfo: PromptInfo }
  | { type: 'SET_PROCESSED_IMAGE'; image: string; promptInfo: PromptInfo }
  | { type: 'SET_DEPTH_MAP'; depthMap: string; promptInfo: PromptInfo }
  | { type: 'SET_STL'; blob: Blob }
  | { type: 'SET_ERROR'; message: string }
  | { type: 'RESET' };

const initialState: GenerationState = {
  step: 'input',
  inputType: null,
  originalImage: null,
  processedImage: null,
  depthMap: null,
  stlBlob: null,
  errorMessage: null,
  currentProcessingStep: null,
  currentPromptInfo: null,
  extractionPromptInfo: null,
  depthMapPromptInfo: null,
};

function reducer(state: GenerationState, action: Action): GenerationState {
  switch (action.type) {
    case 'START_IMAGE_PROCESSING':
      return {
        ...state,
        step: 'processing',
        inputType: 'image',
        originalImage: action.image,
        errorMessage: null,
        currentProcessingStep: 'Extracting subject...',
        currentPromptInfo: action.promptInfo,
      };
    case 'START_PROMPT_PROCESSING':
      return {
        ...state,
        step: 'processing',
        inputType: 'prompt',
        errorMessage: null,
        currentProcessingStep: 'Generating image...',
        currentPromptInfo: action.promptInfo,
      };
    case 'SET_PROCESSING_STEP':
      return {
        ...state,
        currentProcessingStep: action.step,
        currentPromptInfo: action.promptInfo,
      };
    case 'SET_PROCESSED_IMAGE':
      return {
        ...state,
        processedImage: action.image,
        extractionPromptInfo: action.promptInfo,
        currentPromptInfo: action.promptInfo,
      };
    case 'SET_DEPTH_MAP':
      return {
        ...state,
        depthMap: action.depthMap,
        depthMapPromptInfo: action.promptInfo,
        currentPromptInfo: action.promptInfo,
      };
    case 'SET_STL':
      return {
        ...state,
        stlBlob: action.blob,
        step: 'customize',
        currentProcessingStep: null,
        currentPromptInfo: null,
      };
    case 'SET_ERROR':
      return {
        ...state,
        step: 'error',
        errorMessage: action.message,
        currentProcessingStep: null,
        currentPromptInfo: null,
      };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

// Helper to convert template to PromptInfo
function templateToPromptInfo(template: { prompt: string; model: string }): PromptInfo {
  return { promptUsed: template.prompt, modelUsed: template.model };
}

export function useGeneration() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const promptsRef = useRef<PromptTemplates | null>(null);

  // Fetch prompts on mount
  useEffect(() => {
    api.getPrompts().then((prompts) => {
      promptsRef.current = prompts;
    });
  }, []);

  const processImage = useCallback(async (imageBase64: string) => {
    // Ensure prompts are loaded
    if (!promptsRef.current) {
      promptsRef.current = await api.getPrompts();
    }
    const prompts = promptsRef.current;

    dispatch({
      type: 'START_IMAGE_PROCESSING',
      image: imageBase64,
      promptInfo: templateToPromptInfo(prompts.extractSubject),
    });

    try {
      const extractResult = await api.extractSubject(imageBase64);
      dispatch({
        type: 'SET_PROCESSED_IMAGE',
        image: extractResult.image,
        promptInfo: extractResult.promptInfo,
      });

      dispatch({
        type: 'SET_PROCESSING_STEP',
        step: 'Creating depth map...',
        promptInfo: templateToPromptInfo(prompts.createDepthMap),
      });
      const depthResult = await api.createDepthMap(extractResult.image);
      dispatch({
        type: 'SET_DEPTH_MAP',
        depthMap: depthResult.image,
        promptInfo: depthResult.promptInfo,
      });

      dispatch({
        type: 'SET_PROCESSING_STEP',
        step: 'Generating 3D mold...',
        promptInfo: templateToPromptInfo(prompts.generateMold),
      });
      const stlBlob = await api.generateMold(depthResult.image, DEFAULT_MOLD_SETTINGS);
      dispatch({ type: 'SET_STL', blob: stlBlob });
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        message: error instanceof Error ? error.message : 'An error occurred',
      });
    }
  }, []);

  const processPrompt = useCallback(async (prompt: string) => {
    // Ensure prompts are loaded
    if (!promptsRef.current) {
      promptsRef.current = await api.getPrompts();
    }
    const prompts = promptsRef.current;

    // Replace placeholder with actual user prompt for display
    const generatePromptInfo = templateToPromptInfo(prompts.generateImage);
    generatePromptInfo.promptUsed = generatePromptInfo.promptUsed.replace('{user_prompt}', prompt);

    dispatch({
      type: 'START_PROMPT_PROCESSING',
      userPrompt: prompt,
      promptInfo: generatePromptInfo,
    });

    try {
      const generateResult = await api.generateImage(prompt);
      dispatch({
        type: 'SET_PROCESSED_IMAGE',
        image: generateResult.image,
        promptInfo: generateResult.promptInfo,
      });

      dispatch({
        type: 'SET_PROCESSING_STEP',
        step: 'Creating depth map...',
        promptInfo: templateToPromptInfo(prompts.createDepthMap),
      });
      const depthResult = await api.createDepthMap(generateResult.image);
      dispatch({
        type: 'SET_DEPTH_MAP',
        depthMap: depthResult.image,
        promptInfo: depthResult.promptInfo,
      });

      dispatch({
        type: 'SET_PROCESSING_STEP',
        step: 'Generating 3D mold...',
        promptInfo: templateToPromptInfo(prompts.generateMold),
      });
      const stlBlob = await api.generateMold(depthResult.image, DEFAULT_MOLD_SETTINGS);
      dispatch({ type: 'SET_STL', blob: stlBlob });
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        message: error instanceof Error ? error.message : 'An error occurred',
      });
    }
  }, []);

  const regenerateMold = useCallback(
    async (settings: MoldSettings) => {
      if (!state.depthMap) return;

      try {
        const stlBlob = await api.generateMold(state.depthMap, settings);
        dispatch({ type: 'SET_STL', blob: stlBlob });
      } catch (error) {
        dispatch({
          type: 'SET_ERROR',
          message: error instanceof Error ? error.message : 'An error occurred',
        });
      }
    },
    [state.depthMap]
  );

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return {
    state,
    processImage,
    processPrompt,
    regenerateMold,
    reset,
  };
}
