import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Float } from '@react-three/drei';

function ServiceItem({ position, label, color, onClick, disabled }) {
  const meshRef = useRef();
  const [hovered, setHover] = useState(false);

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.5;
    }
  });

  return (
    <Float speed={2} rotationIntensity={1} floatIntensity={2} position={position}>
      <group
        onClick={(e) => {
          e.stopPropagation();
          if (!disabled) onClick();
        }}
        onPointerOver={(e) => { e.stopPropagation(); setHover(true); }}
        onPointerOut={(e) => { e.stopPropagation(); setHover(false); }}
      >
        <mesh ref={meshRef} castShadow receiveShadow>
          <octahedronGeometry args={[0.8, 0]} />
          <meshStandardMaterial 
            color={disabled ? '#6b7280' : hovered ? '#ffffff' : color} 
            wireframe={hovered}
            roughness={0.2}
            metalness={0.8}
          />
        </mesh>
        <Text
          position={[0, -1.2, 0]}
          fontSize={0.25}
          color="white"
          anchorX="center"
          anchorY="middle"
        >
          {label}
        </Text>
      </group>
    </Float>
  );
}

export default function Passenger3DView({ onServiceSelect, isRestricted }) {
  return (
    <div style={{ width: '100%', height: '300px', background: 'rgba(5, 8, 14, 0.45)', border: '1px solid rgba(99, 102, 241, 0.12)', borderRadius: '12px', overflow: 'hidden', marginBottom: '20px', position: 'relative' }}>
      <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 10, color: '#9ca3af', fontSize: '12px' }}>
        Interactive 3D Menu
      </div>
      <Canvas shadows camera={{ position: [0, 2, 8], fov: 45 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
        <pointLight position={[-10, -10, -10]} intensity={0.5} />
        <OrbitControls enableZoom={false} enablePan={false} autoRotate={false} />
        
        <ServiceItem 
          position={[-3, 0, 0]} 
          label="Water" 
          color="#3b82f6" 
          disabled={isRestricted}
          onClick={() => onServiceSelect('Could I get some water please?')} 
        />
        <ServiceItem 
          position={[-1, 0, 0]} 
          label="Blanket" 
          color="#8b5cf6" 
          disabled={isRestricted}
          onClick={() => onServiceSelect('Can I request an extra blanket?')} 
        />
        <ServiceItem 
          position={[1, 0, 0]} 
          label="Lavatory" 
          color="#10b981" 
          disabled={false} // Lavatory info isn't restricted usually, but kept same as App
          onClick={() => onServiceSelect('Is the lavatory currently available?')} 
        />
        <ServiceItem 
          position={[3, 0, 0]} 
          label="Announcement" 
          color="#f59e0b" 
          disabled={false}
          onClick={() => onServiceSelect('What did the captain announce?')} 
        />
      </Canvas>
    </div>
  );
}
