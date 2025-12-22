import base64
import io

import numpy as np
import pytest
from PIL import Image
from stl import mesh as stl_mesh

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

    def test_create_heightmap_mesh(self, mesh_service):
        """Test basic heightmap to mesh conversion."""
        heightmap = np.array([[0.0, 0.5], [0.5, 1.0]], dtype=np.float32)
        scale_xy = 10.0
        scale_z = 20.0

        vertices, faces = mesh_service._create_heightmap_mesh(heightmap, scale_xy, scale_z)

        assert vertices.shape[0] == 4
        assert vertices.shape[1] == 3
        assert len(faces) == 2
        assert len(faces[0]) == 3

    def test_generate_mold_stl_returns_valid_stl(self, mesh_service, sample_depth_map_base64):
        """Test that generated STL is valid binary STL data."""
        stl_data = mesh_service.generate_mold_stl(
            base64_depth_map=sample_depth_map_base64,
            wall_thickness=5.0,
            max_width=50.0,
            max_height=50.0,
            max_depth=20.0,
            include_registration_marks=False,
            include_pouring_channel=False,
        )

        assert isinstance(stl_data, bytes)
        assert len(stl_data) > 0

        buffer = io.BytesIO(stl_data)
        loaded_mesh = stl_mesh.Mesh.from_file(None, fh=buffer)
        assert len(loaded_mesh.vectors) > 0

    def test_generate_mold_stl_with_registration_marks(
        self, mesh_service, sample_depth_map_base64
    ):
        """Test STL generation with registration marks enabled."""
        stl_without = mesh_service.generate_mold_stl(
            base64_depth_map=sample_depth_map_base64,
            include_registration_marks=False,
            include_pouring_channel=False,
        )

        stl_with = mesh_service.generate_mold_stl(
            base64_depth_map=sample_depth_map_base64,
            include_registration_marks=True,
            include_pouring_channel=False,
        )

        assert len(stl_with) > len(stl_without)

    def test_generate_mold_stl_with_pouring_channel(
        self, mesh_service, sample_depth_map_base64
    ):
        """Test STL generation with pouring channel enabled."""
        stl_without = mesh_service.generate_mold_stl(
            base64_depth_map=sample_depth_map_base64,
            include_registration_marks=False,
            include_pouring_channel=False,
        )

        stl_with = mesh_service.generate_mold_stl(
            base64_depth_map=sample_depth_map_base64,
            include_registration_marks=False,
            include_pouring_channel=True,
        )

        assert len(stl_with) > len(stl_without)

    def test_generate_mold_respects_dimensions(self, mesh_service, sample_depth_map_base64):
        """Test that generated mesh respects max dimension constraints."""
        max_width = 80.0
        max_height = 60.0

        stl_data = mesh_service.generate_mold_stl(
            base64_depth_map=sample_depth_map_base64,
            max_width=max_width,
            max_height=max_height,
            include_registration_marks=False,
            include_pouring_channel=False,
        )

        buffer = io.BytesIO(stl_data)
        loaded_mesh = stl_mesh.Mesh.from_file(None, fh=buffer)

        actual_width = loaded_mesh.x.max() - loaded_mesh.x.min()
        actual_height = loaded_mesh.y.max() - loaded_mesh.y.min()

        assert actual_width <= max_width + 20
        assert actual_height <= max_height + 20
