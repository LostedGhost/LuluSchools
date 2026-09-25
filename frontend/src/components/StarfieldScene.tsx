import { useEffect, useRef } from "react";
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  FogExp2,
  PerspectiveCamera,
  Points,
  PointsMaterial,
  Scene,
  WebGLRenderer,
} from "three";
import { usePrefersReducedMotion } from "../hooks/useReducedMotion";

// Au-dela de 1.5, la difference ne se voit plus sur des particules floues, mais
// le cout de rendu croit avec le carre du ratio d'ecran.
const DPR_MAX = 1.5;

/**
 * Fond d'étoiles ambiantes en WebGL (Three.js), chargé à la demande sur la
 * landing page uniquement — Three.js pèse à lui seul plus que tout le reste
 * de l'interface, donc ce composant n'est jamais dans le bundle principal
 * (voir l'import dynamique dans LandingPage.tsx).
 * Purement décoratif (aria-hidden), respecte prefers-reduced-motion, se met
 * en pause quand l'onglet ou le composant n'est pas visible.
 */
export function StarfieldScene() {
  const containerRef = useRef<HTMLDivElement>(null);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    const container = containerRef.current;
    if (!container || reducedMotion) return undefined;

    const isMobile = window.innerWidth < 768;

    const scene = new Scene();
    scene.fog = new FogExp2(0x0b120e, 0.014);

    const camera = new PerspectiveCamera(
      isMobile ? 65 : 55,
      window.innerWidth / window.innerHeight,
      0.1,
      1000,
    );
    camera.position.set(0, 0, isMobile ? 14 : 16);

    const renderer = new WebGLRenderer({
      alpha: true,
      antialias: !isMobile,
      powerPreference: isMobile ? "low-power" : "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_MAX));
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    // Champ d'étoiles — palette institutionnelle (vert de marque, or discret,
    // et une majorité de blanc doux pour rester sobre, pas "néon").
    const starCount = isMobile ? 600 : 1400;
    const geometry = new BufferGeometry();
    const positions = new Float32Array(starCount * 3);
    const colors = new Float32Array(starCount * 3);

    const palette = [
      new Color(0xffffff),
      new Color(0xffffff),
      new Color(0xffffff),
      new Color(0x34c97d),
      new Color(0xf0a83b),
    ];

    for (let i = 0; i < starCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 50;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 50;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 60;

      const color = palette[Math.floor(Math.random() * palette.length)];
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }

    geometry.setAttribute("position", new BufferAttribute(positions, 3));
    geometry.setAttribute("color", new BufferAttribute(colors, 3));

    const material = new PointsMaterial({
      size: isMobile ? 0.14 : 0.17,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: AdditiveBlending,
    });

    const stars = new Points(geometry, material);
    scene.add(stars);

    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    const onMouseMove = (event: MouseEvent) => {
      mouse.targetX = (event.clientX / window.innerWidth - 0.5) * 2;
      mouse.targetY = (event.clientY / window.innerHeight - 0.5) * 2;
    };
    const onResize = () => {
      const mobile = window.innerWidth < 768;
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.fov = mobile ? 65 : 55;
      camera.position.z = mobile ? 14 : 16;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("resize", onResize);

    const debut = performance.now();
    let frame = 0;
    let ongletVisible = !document.hidden;
    let canvasVisible = true;

    const animate = () => {
      const elapsed = (performance.now() - debut) / 1000;
      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;
      stars.rotation.y = elapsed * 0.015 + mouse.x * 0.04;
      stars.rotation.x = mouse.y * 0.04;
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };

    const actualiserBoucle = () => {
      const doitTourner = ongletVisible && canvasVisible;
      if (doitTourner && !frame) {
        frame = requestAnimationFrame(animate);
      } else if (!doitTourner && frame) {
        cancelAnimationFrame(frame);
        frame = 0;
      }
    };

    const onVisibilityChange = () => {
      ongletVisible = !document.hidden;
      actualiserBoucle();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    const observateur =
      typeof IntersectionObserver === "undefined"
        ? null
        : new IntersectionObserver(([entree]) => {
            canvasVisible = entree.isIntersecting;
            actualiserBoucle();
          });
    observateur?.observe(container);

    actualiserBoucle();

    return () => {
      cancelAnimationFrame(frame);
      frame = 0;
      observateur?.disconnect();
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    };
  }, [reducedMotion]);

  return (
    <div
      ref={containerRef}
      style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden" }}
      aria-hidden="true"
    />
  );
}
