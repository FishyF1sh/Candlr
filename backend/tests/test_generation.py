import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_image_base64():
    """Create a simple test image."""
    image = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@pytest.fixture
def sample_depth_map_base64():
    """Create a grayscale depth map for testing."""
    image = Image.new("L", (100, 100), color=128)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class TestHealthEndpoint:
    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestGenerateMoldEndpoint:
    def test_generate_mold_success(self, client, sample_depth_map_base64):
        """Test successful mold generation."""
        response = client.post(
            "/api/generate-mold",
            json={
                "depth_map": sample_depth_map_base64,
                "wall_thickness": 5.0,
                "max_width": 100.0,
                "max_height": 100.0,
                "max_depth": 30.0,
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "content-disposition" in response.headers
        assert len(response.content) > 0

    def test_generate_mold_with_defaults(self, client, sample_depth_map_base64):
        """Test mold generation with default parameters."""
        response = client.post(
            "/api/generate-mold",
            json={"depth_map": sample_depth_map_base64},
        )

        assert response.status_code == 200
        assert len(response.content) > 0

    def test_generate_mold_validation_wall_thickness(self, client, sample_depth_map_base64):
        """Test validation of wall thickness parameter."""
        response = client.post(
            "/api/generate-mold",
            json={
                "depth_map": sample_depth_map_base64,
                "wall_thickness": 1.0,
            },
        )
        assert response.status_code == 422

        response = client.post(
            "/api/generate-mold",
            json={
                "depth_map": sample_depth_map_base64,
                "wall_thickness": 25.0,
            },
        )
        assert response.status_code == 422

    def test_generate_mold_validation_dimensions(self, client, sample_depth_map_base64):
        """Test validation of dimension parameters."""
        response = client.post(
            "/api/generate-mold",
            json={
                "depth_map": sample_depth_map_base64,
                "max_width": 10.0,
            },
        )
        assert response.status_code == 422

        response = client.post(
            "/api/generate-mold",
            json={
                "depth_map": sample_depth_map_base64,
                "max_width": 500.0,
            },
        )
        assert response.status_code == 422

    def test_generate_mold_missing_depth_map(self, client):
        """Test error when depth map is missing."""
        response = client.post("/api/generate-mold", json={})
        assert response.status_code == 422


class TestExtractSubjectEndpoint:
    def test_extract_subject_requires_image(self, client):
        """Test that extract-subject requires an image."""
        response = client.post("/api/extract-subject", json={})
        assert response.status_code == 422


class TestGenerateImageEndpoint:
    def test_generate_image_requires_prompt(self, client):
        """Test that generate-image requires a prompt."""
        response = client.post("/api/generate-image", json={})
        assert response.status_code == 422


class TestCreateDepthMapEndpoint:
    def test_create_depth_map_requires_image(self, client):
        """Test that create-depth-map requires an image."""
        response = client.post("/api/create-depth-map", json={})
        assert response.status_code == 422
