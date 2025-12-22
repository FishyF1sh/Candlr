from typing import Optional
from pydantic import BaseModel, Field


class ImageInput(BaseModel):
    image: str = Field(..., description="Base64 encoded image")


class PromptInput(BaseModel):
    prompt: str = Field(..., description="Text prompt for image generation")


class ProcessedImageResponse(BaseModel):
    processed_image: str = Field(..., description="Base64 encoded processed image")
    prompt_used: str = Field(..., description="The prompt sent to the AI model")
    model_used: str = Field(..., description="The AI model used")


class GeneratedImageResponse(BaseModel):
    generated_image: str = Field(..., description="Base64 encoded generated image")
    prompt_used: str = Field(..., description="The prompt sent to the AI model")
    model_used: str = Field(..., description="The AI model used")


class DepthMapResponse(BaseModel):
    depth_map: str = Field(..., description="Base64 encoded depth map")
    prompt_used: str = Field(..., description="The prompt sent to the AI model")
    model_used: str = Field(..., description="The AI model used")


class MoldGenerationInput(BaseModel):
    depth_map: str = Field(..., description="Base64 encoded depth map")
    wall_thickness: float = Field(default=5.0, ge=2.0, le=20.0, description="Wall thickness in mm")
    max_width: float = Field(default=100.0, ge=20.0, le=300.0, description="Maximum width in mm")
    max_height: float = Field(default=100.0, ge=20.0, le=300.0, description="Maximum height in mm")
    max_depth: float = Field(default=30.0, ge=10.0, le=100.0, description="Maximum depth in mm")
    include_registration_marks: bool = Field(default=True, description="Add corner registration marks")
    include_pouring_channel: bool = Field(default=True, description="Add pouring channel")


class PromptTemplate(BaseModel):
    prompt: str = Field(..., description="The prompt template text")
    model: str = Field(..., description="The AI model used for this operation")


class PromptsResponse(BaseModel):
    extract_subject: PromptTemplate = Field(..., description="Prompt for subject extraction")
    generate_image: PromptTemplate = Field(..., description="Prompt template for image generation (use {user_prompt} placeholder)")
    create_depth_map: PromptTemplate = Field(..., description="Prompt for depth map creation")
    generate_mold: PromptTemplate = Field(..., description="Info for STL mold generation")
