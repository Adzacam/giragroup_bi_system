import React, { useEffect, useRef } from 'react';
import { useTheme } from '../../context/ThemeContext';

export default function IsometricCanvasBackground() {
  const canvasRef = useRef(null);
  const { theme, canvasEnabled } = useTheme();

  useEffect(() => {
    if (!canvasEnabled) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;

    const cols = 18;
    const rows = 12;
    const spacing = 95;
    
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;
    let time = 0;

    const handleMouseMove = (e) => {
      mouseX = (e.clientX / width) * 2 - 1;
      mouseY = (e.clientY / height) * 2 - 1;
    };

    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('resize', handleResize);

    const isDark = theme === 'dark';

    const render = () => {
      ctx.clearRect(0, 0, width, height);
      
      targetX += (mouseX - targetX) * 0.04;
      targetY += (mouseY - targetY) * 0.04;
      time += 0.01;
      
      const scrollOffset = window.scrollY * 0.15;

      ctx.save();
      ctx.translate(width / 2 + targetX * 50, height / 2 - 200 + targetY * 30 - scrollOffset);

      const points = [];

      for (let i = 0; i < rows; i++) {
        for (let j = 0; j < cols; j++) {
          const x = (j - cols / 2) * spacing;
          const y = (i - rows / 2) * spacing;
          
          const dist = Math.sqrt(x * x + y * y);
          const angle = Math.atan2(y, x) + time;
          
          const z = Math.sin(dist * 0.45 - angle) * 24 + (targetY * i * 3);
          
          const isoX = (x - y) * Math.cos(Math.PI / 6);
          const isoY = (x + y) * Math.sin(Math.PI / 6) - z;
          
          points.push({ x: isoX, y: isoY, i, j });
          
          ctx.beginPath();
          ctx.arc(isoX, isoY, 1.8, 0, Math.PI * 2);
          if ((i + j) % 3 === 0) {
            ctx.fillStyle = isDark ? 'rgba(224, 152, 67, 0.65)' : 'rgba(93, 42, 26, 0.4)'; 
          } else {
            ctx.fillStyle = isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(23, 25, 28, 0.15)'; 
          }
          ctx.fill();
        }
      }

      ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(23, 25, 28, 0.05)';
      ctx.lineWidth = 1;
      
      for (let p = 0; p < points.length; p++) {
        const point = points[p];
        if (point.j < cols - 1) {
          const nextPoint = points[p + 1];
          ctx.beginPath();
          ctx.moveTo(point.x, point.y);
          ctx.lineTo(nextPoint.x, nextPoint.y);
          ctx.stroke();
        }
      }
      
      ctx.restore();
      requestAnimationFrame(render);
    };

    const animationId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationId);
    };
  }, [canvasEnabled, theme]);

  if (!canvasEnabled) return null;

  return <canvas id="bg-3d-canvas" ref={canvasRef} />;
}
