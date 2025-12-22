import base64
import io

import numpy as np
import pytest
import trimesh
from PIL import Image

from app.services.mesh import MeshService


@pytest.fixture
def mesh_service():
    return MeshService()


@pytest.fixture
def sample_depth_map_base64():
    """Create a simple gradient depth map for testing."""
    size = 50
    gradient = np.zeros((size, size), dtype=np.uint8)
    for y in range(size):
        for x in range(size):
            dist = np.sqrt((x - size // 2) ** 2 + (y - size // 2) ** 2)
            gradient[y, x] = max(0, 255 - int(dist * 5))

    image = Image.fromarray(gradient)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class TestMeshService:
    def test_decode_depth_map(self, mesh_service, sample_depth_map_base64):
        """Test that depth map decoding works correctly."""
        depth_map = mesh_service._decode_depth_map(sample_depth_map_base64)

        assert isinstance(depth_map, np.ndarray)
        assert depth_map.dtype == np.float32
        assert depth_map.min() >= 0.0
        assert depth_map.max() <= 1.0

    def test_decode_depth_map_with_data_uri(self, mesh_service, sample_depth_map_base64):
        """Test decoding with data URI prefix."""
        data_uri = f"data:image/png;base64,{sample_depth_map_base64}"
        depth_map = mesh_service._decode_depth_map(data_uri)

        assert isinstance(depth_map, np.ndarray)
        assert depth_map.shape[0] > 0
        assert depth_map.shape[1] > 0

    def test_create_heightmap_mesh_fast(self, mesh_service):
        """Test basic heightmap to mesh conversion."""
        heightmap = np.array([[0.0, 0.5], [0.5, 1.0]], dtype=np.float32)
        scale_xy = 10.0
        scale_z = 20.0

        mesh = mesh_service._create_heightmap_mesh_fast(heightmap, scale_xy, scale_z)

        assert isinstance(mesh, trimesh.Trimesh)
        assert len(mesh.vertices) == 4
        assert len(mesh.faces) == 2

    def test_generate_mold_stl_fast_returns_valid_stl(self, mesh_service, sample_depth_map_base64):
        """Test that generated STL is valid binary STL data."""
        stl_data = mesh_service.generate_mold_stl_fast(
            base64_depth_map=sample_depth_map_base64,
            wall_thickness=5.0,
            max_width=50.0,
            max_height=50.0,
            max_depth=20.0,
        )

        assert isinstance(stl_data, bytes)
        assert len(stl_data) > 0

        # Load and verify using trimesh
        buffer = io.BytesIO(stl_data)
        loaded_mesh = trimesh.load(buffer, file_type='stl')
        assert len(loaded_mesh.faces) > 0

    def test_generate_mold_respects_dimensions(self, mesh_service, sample_depth_map_base64):
        """Test that generated mesh respects max dimension constraints."""
        max_width = 80.0
        max_height = 60.0

        stl_data = mesh_service.generate_mold_stl_fast(
            base64_depth_map=sample_depth_map_base64,
            max_width=max_width,
            max_height=max_height,
        )

        buffer = io.BytesIO(stl_data)
        loaded_mesh = trimesh.load(buffer, file_type='stl')

        bounds = loaded_mesh.bounds
        actual_width = bounds[1][0] - bounds[0][0]
        actual_height = bounds[1][1] - bounds[0][1]

        # Allow for walls and groove
        assert actual_width <= max_width + 30
        assert actual_height <= max_height + 30
