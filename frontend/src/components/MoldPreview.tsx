import { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stage } from '@react-three/drei';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import * as THREE from 'three';

interface MoldMeshProps {
  geometry: THREE.BufferGeometry;
}

function MoldMesh({ geometry }: MoldMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.1;
    }
  });

  return (
    <mesh ref={meshRef} geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial color="#c67d5e" roughness={0.4} metalness={0.1} />
    </mesh>
  );
}

interface MoldPreviewProps {
  stlBlob: Blob | null;
}

export function MoldPreview({ stlBlob }: MoldPreviewProps) {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!stlBlob) {
      setGeometry(null);
      return;
    }

    const loader = new STLLoader();
    const url = URL.createObjectURL(stlBlob);

    loader.load(
      url,
      (loadedGeometry) => {
        loadedGeometry.center();
        loadedGeometry.computeVertexNormals();

        const box = new THREE.Box3().setFromBufferAttribute(
          loadedGeometry.getAttribute('position') as THREE.BufferAttribute
        );
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 2 / maxDim;

        loadedGeometry.scale(scale, scale, scale);

        setGeometry(loadedGeometry);
        setError(null);
        URL.revokeObjectURL(url);
      },
      undefined,
      (err) => {
        setError('Failed to load 3D model');
        console.error('STL loading error:', err);
        URL.revokeObjectURL(url);
      }
    );

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [stlBlob]);

  if (error) {
    return (
      <div className="aspect-square bg-cream-dark/50 rounded-sm flex items-center justify-center">
        <p className="text-warm-gray">{error}</p>
      </div>
    );
  }

  if (!geometry) {
    return (
      <div className="aspect-square bg-cream-dark/50 rounded-sm flex items-center justify-center">
        <div className="text-center text-warm-gray">
          <p>No model loaded</p>
        </div>
      </div>
    );
  }

  return (
    <div className="aspect-square bg-gradient-to-br from-cream-dark/80 to-cream-dark/40 rounded-sm overflow-hidden">
      <Canvas shadows camera={{ position: [3, 3, 3], fov: 45 }}>
        <Stage environment="city" intensity={0.5}>
          <MoldMesh geometry={geometry} />
        </Stage>
        <OrbitControls
          enablePan={false}
          minDistance={2}
          maxDistance={10}
          autoRotate={false}
        />
      </Canvas>
    </div>
  );
}
