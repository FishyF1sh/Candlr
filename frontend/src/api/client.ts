import type { MoldSettings, ImageResult, PromptTemplates } from '../types';

const API_BASE = '/api';

export async function getPrompts(): Promise<PromptTemplates> {
  const response = await fetch(`${API_BASE}/prompts`);

  if (!response.ok) {
    throw new Error('Failed to fetch prompts');
  }

  const data = await response.json();
  return {
    extractSubject: { prompt: data.extract_subject.prompt, model: data.extract_subject.model },
    generateImage: { prompt: data.generate_image.prompt, model: data.generate_image.model },
    createDepthMap: { prompt: data.create_depth_map.prompt, model: data.create_depth_map.model },
    generateMold: { prompt: data.generate_mold.prompt, model: data.generate_mold.model },
  };
}

export async function extractSubject(imageBase64: string): Promise<ImageResult> {
  const response = await fetch(`${API_BASE}/extract-subject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageBase64 }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to extract subject');
  }

  const data = await response.json();
  return {
    image: data.processed_image,
    promptInfo: {
      promptUsed: data.prompt_used,
      modelUsed: data.model_used,
    },
  };
}

export async function generateImage(prompt: string): Promise<ImageResult> {
  const response = await fetch(`${API_BASE}/generate-image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate image');
  }

  const data = await response.json();
  return {
    image: data.generated_image,
    promptInfo: {
      promptUsed: data.prompt_used,
      modelUsed: data.model_used,
    },
  };
}

export async function createDepthMap(imageBase64: string): Promise<ImageResult> {
  const response = await fetch(`${API_BASE}/create-depth-map`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageBase64 }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create depth map');
  }

  const data = await response.json();
  return {
    image: data.depth_map,
    promptInfo: {
      promptUsed: data.prompt_used,
      modelUsed: data.model_used,
    },
  };
}

export async function generateMold(
  depthMapBase64: string,
  settings: MoldSettings
): Promise<Blob> {
  const response = await fetch(`${API_BASE}/generate-mold`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      depth_map: depthMapBase64,
      wall_thickness: settings.wallThickness,
      max_width: settings.maxWidth,
      max_height: settings.maxHeight,
      max_depth: settings.maxDepth,
      include_registration_marks: settings.includeRegistrationMarks,
      include_pouring_channel: settings.includePouringChannel,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate mold');
  }

  return response.blob();
}
