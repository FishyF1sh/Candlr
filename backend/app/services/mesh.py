import base64
import io

import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage


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

    def _create_heightmap_mesh_fast(
        self,
        heightmap: np.ndarray,
        scale_xy: float,
        scale_z: float,
    ) -> trimesh.Trimesh:
        """
        Fast vectorized heightmap to mesh conversion using numpy.
        Much faster than the loop-based approach.
        """
        h, w = heightmap.shape

        # Create vertices using vectorized operations
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        x_flat = (x_coords * scale_xy).flatten()
        y_flat = (y_coords * scale_xy).flatten()
        z_flat = (heightmap * scale_z).flatten()
        vertices = np.column_stack([x_flat, y_flat, z_flat]).astype(np.float32)

        # Create faces using vectorized operations
        # For each quad (y, x), we create 2 triangles
        # Vertex indices: v0 = y*w + x, v1 = y*w + x+1, v2 = (y+1)*w + x, v3 = (y+1)*w + x+1
        y_idx, x_idx = np.mgrid[0:h-1, 0:w-1]
        v0 = (y_idx * w + x_idx).flatten()
        v1 = (y_idx * w + x_idx + 1).flatten()
        v2 = ((y_idx + 1) * w + x_idx).flatten()
        v3 = ((y_idx + 1) * w + x_idx + 1).flatten()

        # Two triangles per quad
        faces1 = np.column_stack([v0, v1, v2])
        faces2 = np.column_stack([v1, v3, v2])
        faces = np.vstack([faces1, faces2])

        return trimesh.Trimesh(vertices=vertices, faces=faces)

    def generate_mold_stl_fast(
        self,
        base64_depth_map: str,
        wall_thickness: float = 5.0,
        max_width: float = 100.0,
        max_height: float = 100.0,
        max_depth: float = 30.0,
    ) -> bytes:
        """
        Fast STL mold generation using vectorized numpy operations.
        Much faster than loop-based approaches.
        """
        import time
        start = time.time()
        last = start

        def log_time(step: str):
            nonlocal last
            now = time.time()
            print(f"[Mesh] {step}: {(now - last)*1000:.0f}ms")
            last = now

        depth_map = self._decode_depth_map(base64_depth_map)
        log_time("Decode depth map")

        # Keep original orientation: white (high) = raised areas in mold
        # Smooth to reduce noise
        depth_map = ndimage.gaussian_filter(depth_map, sigma=2.0)
        log_time("Smooth depth map")

        h, w = depth_map.shape
        aspect = w / h

        # Calculate target dimensions
        if aspect > max_width / max_height:
            target_w = max_width
        else:
            target_w = max_height * aspect

        scale_xy = target_w / w
        scale_z = max_depth

        # Downsample for speed - 500x500 is good balance
        max_resolution = 500
        if max(h, w) > max_resolution:
            scale_factor = max_resolution / max(h, w)
            new_h = int(h * scale_factor)
            new_w = int(w * scale_factor)
            img = Image.fromarray((depth_map * 255).astype(np.uint8))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            depth_map = np.array(img, dtype=np.float32) / 255.0
            scale_xy = target_w / new_w
            log_time(f"Resize to {new_w}x{new_h}")

        # Generate mesh using fast vectorized method
        mesh = self._create_heightmap_mesh_fast(depth_map, scale_xy, scale_z)
        log_time(f"Create mesh ({len(mesh.faces)} faces)")

        # Smooth only the relief mesh (not walls/base)
        trimesh.smoothing.filter_laplacian(mesh, lamb=0.5, iterations=3)
        log_time("Smooth relief mesh")

        # Get mesh bounds
        bounds = mesh.bounds
        min_x, min_y, min_z = bounds[0]
        max_x, max_y, max_z = bounds[1]

        # Groove dimensions for silicone wall
        groove_width = wall_thickness
        groove_depth = wall_thickness * 0.5  # Groove is half the wall thickness deep
        groove_offset = wall_thickness * 0.5  # Gap between relief and groove

        # Wall height should be above the highest point of the relief
        wall_top_z = max_z + wall_thickness
        base_z = 0  # Base at z=0

        # Total mold dimensions including groove
        total_width = (max_x - min_x) + (groove_offset + groove_width) * 2 + wall_thickness * 2
        total_height = (max_y - min_y) + (groove_offset + groove_width) * 2 + wall_thickness * 2
        total_depth = wall_top_z + wall_thickness  # Add base thickness

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Create base plate
        base_plate = trimesh.creation.box(
            extents=[total_width, total_height, wall_thickness],
            transform=trimesh.transformations.translation_matrix([
                center_x,
                center_y,
                -wall_thickness / 2,
            ])
        )
        log_time("Create base plate")

        # Create groove (rectangular channel around the relief)
        # Outer boundary of groove
        groove_outer_w = (max_x - min_x) + (groove_offset + groove_width) * 2
        groove_outer_h = (max_y - min_y) + (groove_offset + groove_width) * 2
        # Inner boundary of groove
        groove_inner_w = (max_x - min_x) + groove_offset * 2
        groove_inner_h = (max_y - min_y) + groove_offset * 2

        # Create groove as outer box minus inner box
        groove_outer = trimesh.creation.box(
            extents=[groove_outer_w, groove_outer_h, groove_depth],
            transform=trimesh.transformations.translation_matrix([
                center_x,
                center_y,
                groove_depth / 2,
            ])
        )
        groove_inner = trimesh.creation.box(
            extents=[groove_inner_w, groove_inner_h, groove_depth + 1],
            transform=trimesh.transformations.translation_matrix([
                center_x,
                center_y,
                groove_depth / 2,
            ])
        )

        try:
            groove = groove_outer.difference(groove_inner)
            log_time("Create groove (boolean)")
        except Exception as e:
            print(f"[Mesh] Groove boolean failed: {e}")
            groove = None

        # Create outer walls
        outer_box = trimesh.creation.box(
            extents=[total_width, total_height, wall_top_z],
            transform=trimesh.transformations.translation_matrix([
                center_x,
                center_y,
                wall_top_z / 2,
            ])
        )
        inner_box = trimesh.creation.box(
            extents=[total_width - wall_thickness * 2, total_height - wall_thickness * 2, wall_top_z + 1],
            transform=trimesh.transformations.translation_matrix([
                center_x,
                center_y,
                wall_top_z / 2,
            ])
        )

        try:
            walls = outer_box.difference(inner_box)
            log_time("Create walls (boolean)")
        except Exception as e:
            print(f"[Mesh] Walls boolean failed: {e}")
            walls = None

        # Combine all parts
        parts = [mesh, base_plate]
        if groove is not None:
            parts.append(groove)
        if walls is not None:
            parts.append(walls)

        combined = trimesh.util.concatenate(parts)
        log_time("Combine meshes")

        # Fix normals - ensure they're consistent and pointing outward
        combined.fix_normals()
        log_time("Fix normals")

        # Export to STL
        stl_data = combined.export(file_type='stl')
        log_time("Export STL")

        print(f"[Mesh] TOTAL: {(time.time() - start)*1000:.0f}ms")
        return stl_data

mesh_service = MeshService()
