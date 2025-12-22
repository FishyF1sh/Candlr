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

    def _find_wick_position(
        self,
        depth_map: np.ndarray,
        scale_xy: float,
        scale_z: float,
        search_radius_ratio: float = 0.3,
    ) -> tuple:
        """
        Find the best position for the wick hole.
        Looks for a high z-value point near the center of the depth map.

        Args:
            depth_map: The depth map array
            scale_xy: Scale factor for x/y coordinates
            scale_z: Scale factor for z coordinates
            search_radius_ratio: How far from center to search (as ratio of image size)

        Returns:
            (x, y, z) position for the wick in mesh coordinates
        """
        h, w = depth_map.shape
        center_y, center_x = h // 2, w // 2

        # Define search region around center
        search_radius_y = int(h * search_radius_ratio)
        search_radius_x = int(w * search_radius_ratio)

        y_min = max(0, center_y - search_radius_y)
        y_max = min(h, center_y + search_radius_y)
        x_min = max(0, center_x - search_radius_x)
        x_max = min(w, center_x + search_radius_x)

        # Extract search region
        search_region = depth_map[y_min:y_max, x_min:x_max]

        # Find the highest point in the search region
        local_y, local_x = np.unravel_index(np.argmax(search_region), search_region.shape)

        # Convert back to global coordinates
        best_y = y_min + local_y
        best_x = x_min + local_x
        best_z = depth_map[best_y, best_x] * scale_z

        # Convert to mesh coordinates
        mesh_x = best_x * scale_xy
        mesh_y = best_y * scale_xy

        return mesh_x, mesh_y, best_z

    def generate_mold_stl_fast(
        self,
        base64_depth_map: str,
        wall_thickness: float = 5.0,
        max_width: float = 100.0,
        max_height: float = 100.0,
        max_depth: float = 30.0,
        wick_enabled: bool = True,
        wick_diameter: float = 1.5,
        wick_length: float = 10.0,
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

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Calculate wick position and adjust wall height if needed BEFORE creating walls
        wick = None
        wick_x, wick_y, wick_z = center_x, center_y, 0
        if wick_enabled:
            # Place wick at the center of the mesh
            wick_x = center_x
            wick_y = center_y

            # Get the z value at the center from the mesh vertices
            # Find vertices closest to center
            vertices = mesh.vertices
            distances = np.sqrt((vertices[:, 0] - center_x)**2 + (vertices[:, 1] - center_y)**2)
            closest_idx = np.argmin(distances)
            wick_z = vertices[closest_idx, 2]

            # Calculate required wick top position
            wick_top_z = wick_z + wick_length

            # Update wall height if wick extends beyond current wall height
            if wick_top_z > wall_top_z:
                wall_top_z = wick_top_z + wall_thickness
                print(f"[Mesh] Extended wall height to {wall_top_z:.1f}mm to accommodate wick")

        # Total mold dimensions including groove
        total_width = (max_x - min_x) + (groove_offset + groove_width) * 2 + wall_thickness * 2
        total_height = (max_y - min_y) + (groove_offset + groove_width) * 2 + wall_thickness * 2
        total_depth = wall_top_z + wall_thickness  # Add base thickness

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

        # Create outer walls (using potentially extended wall_top_z)
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

        # Create wick cylinder now that wall height is finalized
        if wick_enabled:
            # The cylinder goes from below the base plate through the relief
            wick_bottom_z = -wall_thickness - 1  # Below base plate
            wick_top_z = wick_z + wick_length  # Extend wick_length above the attachment point

            wick_height = wick_top_z - wick_bottom_z
            wick_center_z = (wick_bottom_z + wick_top_z) / 2

            wick = trimesh.creation.cylinder(
                radius=wick_diameter / 2,
                height=wick_height,
                sections=32,
            )
            # Move wick to the correct position
            wick.apply_translation([wick_x, wick_y, wick_center_z])
            log_time(f"Create wick at center ({wick_x:.1f}, {wick_y:.1f}, z={wick_z:.1f})")

        # Combine all parts
        parts = [mesh, base_plate]
        if groove is not None:
            parts.append(groove)
        if walls is not None:
            parts.append(walls)
        if wick is not None:
            parts.append(wick)

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
