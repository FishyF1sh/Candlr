import base64
import io
import os
import tempfile
from typing import Tuple, List

import numpy as np
from PIL import Image
from scipy import ndimage
from stl import mesh as stl_mesh
from stl import Mode as StlMode


class MeshService:
    def __init__(self):
        pass

    def _decode_depth_map(self, base64_depth_map: str) -> np.ndarray:
        """Decode base64 depth map to numpy array."""
        if "," in base64_depth_map:
            base64_depth_map = base64_depth_map.split(",")[1]
        image_data = base64.b64decode(base64_depth_map)
        image = Image.open(io.BytesIO(image_data)).convert("L")
        return np.array(image, dtype=np.float32) / 255.0

    def _create_heightmap_mesh(
        self,
        heightmap: np.ndarray,
        scale_xy: float,
        scale_z: float,
    ) -> Tuple[np.ndarray, List[List[int]]]:
        """
        Create vertices and faces from a heightmap.
        Returns vertices (Nx3) and faces (list of [v0, v1, v2] indices).
        Uses consistent counter-clockwise winding for outward-facing normals.
        """
        h, w = heightmap.shape
        vertices = []
        vertex_indices = np.zeros((h, w), dtype=np.int32)

        idx = 0
        for y in range(h):
            for x in range(w):
                z = heightmap[y, x] * scale_z
                vertices.append([x * scale_xy, y * scale_xy, z])
                vertex_indices[y, x] = idx
                idx += 1

        vertices = np.array(vertices, dtype=np.float32)
        faces = []

        # Create faces with consistent winding (counter-clockwise when viewed from above)
        for y in range(h - 1):
            for x in range(w - 1):
                v0 = vertex_indices[y, x]
                v1 = vertex_indices[y, x + 1]
                v2 = vertex_indices[y + 1, x]
                v3 = vertex_indices[y + 1, x + 1]

                # Two triangles per quad, counter-clockwise winding for upward normals
                faces.append([v0, v1, v2])  # Triangle 1
                faces.append([v1, v3, v2])  # Triangle 2

        return vertices, faces

    def _add_walls_and_base(
        self,
        vertices: np.ndarray,
        faces: List[List[int]],
        heightmap: np.ndarray,
        wall_thickness: float,
        scale_xy: float,
        base_z: float,
    ) -> Tuple[np.ndarray, List[List[int]]]:
        """Add walls around the perimeter and a solid base plate."""
        h, w = heightmap.shape
        vertex_list = vertices.tolist()
        face_list = list(faces)

        # Create base vertices (at base_z level)
        base_vertex_start = len(vertex_list)
        for y in range(h):
            for x in range(w):
                vertex_list.append([x * scale_xy, y * scale_xy, base_z])

        # Base faces (facing down, so clockwise when viewed from above)
        for y in range(h - 1):
            for x in range(w - 1):
                v0 = base_vertex_start + y * w + x
                v1 = base_vertex_start + y * w + x + 1
                v2 = base_vertex_start + (y + 1) * w + x
                v3 = base_vertex_start + (y + 1) * w + x + 1
                # Clockwise winding for downward-facing normals
                face_list.append([v0, v2, v1])
                face_list.append([v1, v2, v3])

        # Connect top surface edges to base edges (side walls of the cavity)
        # Front edge (y = 0)
        for x in range(w - 1):
            top_left = x
            top_right = x + 1
            base_left = base_vertex_start + x
            base_right = base_vertex_start + x + 1
            # Wall facing inward (toward negative y)
            face_list.append([top_left, base_left, top_right])
            face_list.append([top_right, base_left, base_right])

        # Back edge (y = h-1)
        for x in range(w - 1):
            top_left = (h - 1) * w + x
            top_right = (h - 1) * w + x + 1
            base_left = base_vertex_start + (h - 1) * w + x
            base_right = base_vertex_start + (h - 1) * w + x + 1
            # Wall facing inward (toward positive y)
            face_list.append([top_left, top_right, base_left])
            face_list.append([top_right, base_right, base_left])

        # Left edge (x = 0)
        for y in range(h - 1):
            top_bottom = y * w
            top_top = (y + 1) * w
            base_bottom = base_vertex_start + y * w
            base_top = base_vertex_start + (y + 1) * w
            # Wall facing inward (toward negative x)
            face_list.append([top_bottom, top_top, base_bottom])
            face_list.append([top_top, base_top, base_bottom])

        # Right edge (x = w-1)
        for y in range(h - 1):
            top_bottom = y * w + (w - 1)
            top_top = (y + 1) * w + (w - 1)
            base_bottom = base_vertex_start + y * w + (w - 1)
            base_top = base_vertex_start + (y + 1) * w + (w - 1)
            # Wall facing inward (toward positive x)
            face_list.append([top_bottom, base_bottom, top_top])
            face_list.append([top_top, base_bottom, base_top])

        # Now add outer walls
        outer_wall_start = len(vertex_list)
        outer_offset = wall_thickness
        actual_w = (w - 1) * scale_xy
        actual_h = (h - 1) * scale_xy

        # Outer wall corners (8 vertices: 4 at top z=0, 4 at bottom z=base_z)
        outer_corners_top = [
            [-outer_offset, -outer_offset, 0],
            [actual_w + outer_offset, -outer_offset, 0],
            [actual_w + outer_offset, actual_h + outer_offset, 0],
            [-outer_offset, actual_h + outer_offset, 0],
        ]
        outer_corners_base = [
            [-outer_offset, -outer_offset, base_z],
            [actual_w + outer_offset, -outer_offset, base_z],
            [actual_w + outer_offset, actual_h + outer_offset, base_z],
            [-outer_offset, actual_h + outer_offset, base_z],
        ]

        for v in outer_corners_top:
            vertex_list.append(v)
        for v in outer_corners_base:
            vertex_list.append(v)

        # Outer wall faces (4 walls)
        # Each wall: 2 triangles, outward-facing normals
        # Front wall (y = -outer_offset)
        t0, t1 = outer_wall_start, outer_wall_start + 1
        b0, b1 = outer_wall_start + 4, outer_wall_start + 5
        face_list.append([t0, b0, t1])
        face_list.append([t1, b0, b1])

        # Right wall (x = actual_w + outer_offset)
        t1, t2 = outer_wall_start + 1, outer_wall_start + 2
        b1, b2 = outer_wall_start + 5, outer_wall_start + 6
        face_list.append([t1, b1, t2])
        face_list.append([t2, b1, b2])

        # Back wall (y = actual_h + outer_offset)
        t2, t3 = outer_wall_start + 2, outer_wall_start + 3
        b2, b3 = outer_wall_start + 6, outer_wall_start + 7
        face_list.append([t2, b2, t3])
        face_list.append([t3, b2, b3])

        # Left wall (x = -outer_offset)
        t3, t0 = outer_wall_start + 3, outer_wall_start
        b3, b0 = outer_wall_start + 7, outer_wall_start + 4
        face_list.append([t3, b3, t0])
        face_list.append([t0, b3, b0])

        # Top rim (connects outer wall top to inner surface edges)
        # This requires connecting the outer corners to the inner edge vertices
        # Front rim
        for x in range(w):
            inner_v = x
            if x == 0:
                outer_left = outer_wall_start  # top-left corner
            else:
                outer_left = None
            if x == w - 1:
                outer_right = outer_wall_start + 1  # top-right corner

        # For simplicity, add a flat top rim connecting outer to inner
        # Front edge rim
        inner_front_left = 0
        inner_front_right = w - 1
        outer_front_left = outer_wall_start
        outer_front_right = outer_wall_start + 1
        face_list.append([outer_front_left, inner_front_left, outer_front_right])
        face_list.append([outer_front_right, inner_front_left, inner_front_right])

        # Right edge rim
        inner_right_front = w - 1
        inner_right_back = (h - 1) * w + (w - 1)
        outer_right_front = outer_wall_start + 1
        outer_right_back = outer_wall_start + 2
        face_list.append([outer_right_front, inner_right_front, outer_right_back])
        face_list.append([outer_right_back, inner_right_front, inner_right_back])

        # Back edge rim
        inner_back_right = (h - 1) * w + (w - 1)
        inner_back_left = (h - 1) * w
        outer_back_right = outer_wall_start + 2
        outer_back_left = outer_wall_start + 3
        face_list.append([outer_back_right, inner_back_right, outer_back_left])
        face_list.append([outer_back_left, inner_back_right, inner_back_left])

        # Left edge rim
        inner_left_back = (h - 1) * w
        inner_left_front = 0
        outer_left_back = outer_wall_start + 3
        outer_left_front = outer_wall_start
        face_list.append([outer_left_back, inner_left_back, outer_left_front])
        face_list.append([outer_left_front, inner_left_back, inner_left_front])

        # Outer base (bottom face of outer walls)
        ob0, ob1, ob2, ob3 = outer_wall_start + 4, outer_wall_start + 5, outer_wall_start + 6, outer_wall_start + 7
        face_list.append([ob0, ob1, ob2])
        face_list.append([ob0, ob2, ob3])

        return np.array(vertex_list, dtype=np.float32), face_list

    def _add_registration_marks(
        self,
        vertices: np.ndarray,
        faces: List[List[int]],
        width: float,
        height: float,
        wall_thickness: float,
    ) -> Tuple[np.ndarray, List[List[int]]]:
        """Add small pyramid registration marks at corners."""
        vertex_list = vertices.tolist()
        face_list = list(faces)
        mark_size = wall_thickness * 0.5
        mark_height = wall_thickness * 0.3

        corners = [
            (-wall_thickness / 2, -wall_thickness / 2),
            (width + wall_thickness / 2, -wall_thickness / 2),
            (width + wall_thickness / 2, height + wall_thickness / 2),
            (-wall_thickness / 2, height + wall_thickness / 2),
        ]

        for cx, cy in corners:
            base_idx = len(vertex_list)
            # Base vertices (at z=0)
            vertex_list.append([cx - mark_size / 2, cy - mark_size / 2, 0])
            vertex_list.append([cx + mark_size / 2, cy - mark_size / 2, 0])
            vertex_list.append([cx + mark_size / 2, cy + mark_size / 2, 0])
            vertex_list.append([cx - mark_size / 2, cy + mark_size / 2, 0])
            # Apex (pointing down)
            vertex_list.append([cx, cy, -mark_height])

            apex = base_idx + 4
            # Side faces (outward normals)
            face_list.append([base_idx, apex, base_idx + 1])
            face_list.append([base_idx + 1, apex, base_idx + 2])
            face_list.append([base_idx + 2, apex, base_idx + 3])
            face_list.append([base_idx + 3, apex, base_idx])
            # Base face (upward normal)
            face_list.append([base_idx, base_idx + 1, base_idx + 2])
            face_list.append([base_idx, base_idx + 2, base_idx + 3])

        return np.array(vertex_list, dtype=np.float32), face_list

    def _add_pouring_channel(
        self,
        vertices: np.ndarray,
        faces: List[List[int]],
        width: float,
        height: float,
        depth: float,
    ) -> Tuple[np.ndarray, List[List[int]]]:
        """Add a funnel-shaped pouring channel at the top center."""
        vertex_list = vertices.tolist()
        face_list = list(faces)

        cx = width / 2
        cy = height / 2
        top_radius = min(width, height) * 0.12
        bottom_radius = top_radius * 0.4
        channel_depth = depth * 0.4

        segments = 16
        base_idx = len(vertex_list)

        # Top ring (at z=0)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            vertex_list.append([
                cx + top_radius * np.cos(angle),
                cy + top_radius * np.sin(angle),
                0,
            ])

        # Bottom ring (at z=channel_depth, inside the mold)
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            vertex_list.append([
                cx + bottom_radius * np.cos(angle),
                cy + bottom_radius * np.sin(angle),
                channel_depth,
            ])

        # Side faces of the funnel (inward normals since it's a hole)
        for i in range(segments):
            i_next = (i + 1) % segments
            v0 = base_idx + i
            v1 = base_idx + i_next
            v2 = base_idx + segments + i
            v3 = base_idx + segments + i_next
            face_list.append([v0, v1, v2])
            face_list.append([v1, v3, v2])

        # Bottom cap of the funnel
        center_idx = len(vertex_list)
        vertex_list.append([cx, cy, channel_depth])
        for i in range(segments):
            i_next = (i + 1) % segments
            face_list.append([
                base_idx + segments + i_next,
                base_idx + segments + i,
                center_idx,
            ])

        return np.array(vertex_list, dtype=np.float32), face_list

    def generate_mold_stl(
        self,
        base64_depth_map: str,
        wall_thickness: float = 5.0,
        max_width: float = 100.0,
        max_height: float = 100.0,
        max_depth: float = 30.0,
        include_registration_marks: bool = True,
        include_pouring_channel: bool = True,
    ) -> bytes:
        """
        Generate an STL mold from a depth map.

        The mold is a negative of the candle shape - when you pour silicone into
        this mold, then pour wax into the silicone mold, you get the original shape.
        """
        depth_map = self._decode_depth_map(base64_depth_map)

        # Invert: high values in depth map become low points in mold (cavity)
        depth_map = 1.0 - depth_map

        # Smooth the depth map to reduce noise
        depth_map = ndimage.gaussian_filter(depth_map, sigma=1.5)

        h, w = depth_map.shape
        aspect = w / h

        # Calculate target dimensions
        if aspect > max_width / max_height:
            target_w = max_width
            target_h = max_width / aspect
        else:
            target_h = max_height
            target_w = max_height * aspect

        scale_xy = target_w / w
        scale_z = max_depth

        # Reduce resolution for mesh generation (too many vertices = slow)
        target_resolution = 200
        if max(h, w) > target_resolution:
            scale_factor = target_resolution / max(h, w)
            new_h = int(h * scale_factor)
            new_w = int(w * scale_factor)
            img = Image.fromarray((depth_map * 255).astype(np.uint8))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            depth_map = np.array(img, dtype=np.float32) / 255.0
            scale_xy = target_w / new_w

        base_z = -wall_thickness

        # Build the mesh
        vertices, faces = self._create_heightmap_mesh(depth_map, scale_xy, scale_z)
        vertices, faces = self._add_walls_and_base(
            vertices, faces, depth_map, wall_thickness, scale_xy, base_z
        )

        actual_width = (depth_map.shape[1] - 1) * scale_xy
        actual_height = (depth_map.shape[0] - 1) * scale_xy

        if include_registration_marks:
            vertices, faces = self._add_registration_marks(
                vertices, faces, actual_width, actual_height, wall_thickness
            )

        if include_pouring_channel:
            vertices, faces = self._add_pouring_channel(
                vertices, faces, actual_width, actual_height, max_depth
            )

        # Create STL mesh
        faces_array = np.array(faces)
        stl = stl_mesh.Mesh(np.zeros(len(faces_array), dtype=stl_mesh.Mesh.dtype))

        for i, face in enumerate(faces_array):
            for j in range(3):
                stl.vectors[i][j] = vertices[face[j]]

        # CRITICAL: Update normals for proper rendering
        stl.update_normals()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
            tmp_path = tmp.name

        stl.save(tmp_path, mode=StlMode.BINARY)

        with open(tmp_path, "rb") as f:
            data = f.read()

        os.unlink(tmp_path)

        return data


mesh_service = MeshService()
