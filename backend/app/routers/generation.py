from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models.schemas import (
    DepthMapResponse,
    GeneratedImageResponse,
    ImageInput,
    MoldGenerationInput,
    ProcessedImageResponse,
    PromptInput,
    PromptsResponse,
)
from app.services.gemini import gemini_service
from app.services.mesh import mesh_service

router = APIRouter()


@router.get("/prompts", response_model=PromptsResponse)
async def get_prompts():
    """
    Get all prompt templates used by the AI models.
    Useful for displaying prompts in the UI during processing.
    """
    return gemini_service.get_prompt_templates()


@router.post("/extract-subject", response_model=ProcessedImageResponse)
async def extract_subject(input_data: ImageInput):
    """
    Extract the main subject from an uploaded image and optimize it for candle mold creation.
    """
    try:
        result = await gemini_service.extract_subject(input_data.image)
        return ProcessedImageResponse(
            processed_image=result.image_base64,
            prompt_used=result.prompt_used,
            model_used=result.model_used,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract subject: {str(e)}")


@router.post("/generate-image", response_model=GeneratedImageResponse)
async def generate_image(input_data: PromptInput):
    """
    Generate an image from a text prompt, optimized for candle mold creation.
    """
    try:
        result = await gemini_service.generate_image_from_prompt(input_data.prompt)
        return GeneratedImageResponse(
            generated_image=result.image_base64,
            prompt_used=result.prompt_used,
            model_used=result.model_used,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")


@router.post("/create-depth-map", response_model=DepthMapResponse)
async def create_depth_map(input_data: ImageInput):
    """
    Create a depth map from an image for 3D mold generation.
    """
    try:
        result = await gemini_service.create_depth_map(input_data.image)
        return DepthMapResponse(
            depth_map=result.image_base64,
            prompt_used=result.prompt_used,
            model_used=result.model_used,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create depth map: {str(e)}")


@router.post("/generate-mold")
async def generate_mold(input_data: MoldGenerationInput):
    """
    Generate an STL mold file from a depth map with specified parameters.
    """
    try:
        stl_data = mesh_service.generate_mold_stl_fast(
            base64_depth_map=input_data.depth_map,
            wall_thickness=input_data.wall_thickness,
            max_width=input_data.max_width,
            max_height=input_data.max_height,
            max_depth=input_data.max_depth,
        )
        return Response(
            content=stl_data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename=candle_mold.stl"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate mold: {str(e)}")
