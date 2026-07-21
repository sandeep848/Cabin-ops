import React, { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Html } from '@react-three/drei';

function Seat({ position, label, isOccupied, hasRequest, requestIntent, onClick }) {
  const meshRef = useRef();

  useFrame((state) => {
    if (hasRequest && meshRef.current) {
      meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 5) * 0.1;
    }
  });

  const color = hasRequest ? '#ef4444' : isOccupied ? '#3b82f6' : '#9ca3af';

  return (
    <group position={position} onClick={onClick}>
      <mesh ref={meshRef} castShadow receiveShadow>
        <boxGeometry args={[0.6, 0.5, 0.6]} />
        <meshStandardMaterial color={color} roughness={0.3} />
      </mesh>
      {hasRequest && (
        <Html position={[0, 0.8, 0]} center>
          <div style={{
            background: 'rgba(239, 68, 68, 0.9)',
            color: 'white',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: 'bold',
            whiteSpace: 'nowrap',
            pointerEvents: 'none'
          }}>
            {requestIntent}
          </div>
        </Html>
      )}
      <Text
        position={[0, 0.3, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.2}
        color="white"
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </Text>
    </group>
  );
}

export default function Cabin3DView({ tasks, flightContext, onSeatSelect }) {
  const seats = useMemo(() => {
    const arr = [];
    const rows = 15; // Simplified rows for 3D visualization
    const cols = ['A', 'B', 'C', 'D', 'E', 'F'];
    
    for (let r = 1; r <= rows; r++) {
      for (let c = 0; c < cols.length; c++) {
        const seatLabel = `${r}${cols[c]}`;
        const activeTask = tasks.find(t => t.seat === seatLabel && t.status !== 'completed' && t.status !== 'resolved');
        
        const x = (c < 3 ? c - 1.5 : c - 1) * 1.0 - 0.5;
        const z = r * 1.2 - (rows * 1.2) / 2;
        
        arr.push({
          id: seatLabel,
          position: [x, 0, z],
          label: seatLabel,
          hasRequest: !!activeTask,
          requestIntent: activeTask ? (activeTask.intent || 'Request') : '',
        });
      }
    }
    return arr;
  }, [tasks]);

  return (
    <div style={{ width: '100%', height: '400px', background: '#111827', borderRadius: '12px', overflow: 'hidden', position: 'relative' }}>
      <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 10, color: 'white', background: 'rgba(0,0,0,0.5)', padding: '8px', borderRadius: '8px' }}>
        <h3 style={{ margin: 0, fontSize: '14px' }}>Flight Phase: {flightContext?.flight_phase || 'Unknown'}</h3>
        <p style={{ margin: '4px 0 0 0', fontSize: '12px' }}>Active Requests: {tasks.filter(t => t.status !== 'completed').length}</p>
      </div>
      <Canvas shadows camera={{ position: [0, 8, 12], fov: 45 }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
        <OrbitControls enablePan={true} enableZoom={true} enableRotate={true} />
        
        {/* Floor */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.25, 0]} receiveShadow>
          <planeGeometry args={[10, 30]} />
          <meshStandardMaterial color="#374151" />
        </mesh>

        {seats.map((seat) => (
          <Seat
            key={seat.id}
            position={seat.position}
            label={seat.label}
            hasRequest={seat.hasRequest}
            requestIntent={seat.requestIntent}
            onClick={() => onSeatSelect(seat.id)}
          />
        ))}
      </Canvas>
    </div>
  );
}
