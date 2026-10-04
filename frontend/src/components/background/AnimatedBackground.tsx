import { useEffect, useState } from "react";

export function AnimatedBackground() {
  const [mousePos, setMousePos] = useState({ x: 50, y: 30 });

  useEffect(() => {
    let frameId: number;
    const handleMouseMove = (e: MouseEvent) => {
      cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(() => {
        const x = (e.clientX / window.innerWidth) * 100;
        const y = (e.clientY / window.innerHeight) * 100;
        setMousePos({ x, y });
      });
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(frameId);
    };
  }, []);

  return (
    <div className="liquid-bg-viewport" aria-hidden="true">
      {/* Deep atmospheric gradient base */}
      <div className="liquid-bg-base" />

      {/* Floating Violet Atmospheric Orb */}
      <div className="liquid-orb liquid-orb-violet" />

      {/* Floating Electric Blue Atmospheric Orb */}
      <div className="liquid-orb liquid-orb-blue" />

      {/* Secondary Indigo Soft Glow */}
      <div className="liquid-orb liquid-orb-indigo" />

      {/* Interactive mouse-following soft ambient spotlight */}
      <div
        className="liquid-mouse-glow"
        style={{
          left: `${mousePos.x}%`,
          top: `${mousePos.y}%`,
        }}
      />

      {/* Ambient particle shimmer grid */}
      <div className="liquid-particle-field">
        <span className="particle p-1" />
        <span className="particle p-2" />
        <span className="particle p-3" />
        <span className="particle p-4" />
        <span className="particle p-5" />
        <span className="particle p-6" />
        <span className="particle p-7" />
        <span className="particle p-8" />
      </div>

      {/* Subtle organic noise texture overlay */}
      <div className="liquid-noise-overlay" />
    </div>
  );
}
