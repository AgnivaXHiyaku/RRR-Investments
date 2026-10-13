// The 3D stage. One fixed WebGL canvas sits behind the page; Blender-built
// models (public/models/*.glb) are "actors" that enter and leave as the
// story's chapters scroll past. Every actor has a procedural fallback so the
// page still works if a model fails to load.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

const SAFFRON = new THREE.Color('#f2a43a');
const GOLD = new THREE.Color('#f2c14e');
const ROYAL = new THREE.Color('#2b58d6');

// Where each actor stands for each scene state. x/y in world units at z=0
// (camera at z=7, fov 32 => roughly ±2 units of vertical half-height).
const STATES = {
  'monolith':       { actor: 'monolith', x: 1.55, y: -1.7,  z: 0,    ry: -0.55, s: 1.5,  spread: 0 },
  'monolith-side':  { actor: 'monolith', x: 1.85, y: -1.35, z: -0.6, ry: 0.35,  s: 1.25, spread: 0.15 },
  'monolith-split': { actor: 'monolith', x: 2.6,  y: -1.3,  z: -3.4, ry: -0.3,  s: 1.5,  spread: 1, dim: 0.4 },
  'monolith-fund':  { actor: 'monolith', x: 2.6,  y: -1.6,  z: -3.2, ry: -0.9,  s: 1.4,  spread: 0.3, dim: 0.5 },
  'monolith-end':   { actor: 'monolith', x: 0.1,  y: -1.5,  z: -4.5, ry: 0.2,   s: 1.7,  spread: 0.05, dim: 0.4 },
  'shankha':        { actor: 'shankha',  x: 1.6,  y: -0.75, z: 0,    ry: -0.6,  s: 1.45 },
  'urli':           { actor: 'urli',     x: -1.75, y: -0.55, z: 0,   ry: 0,     s: 1.25, rx: 0.42 },
  'diya':           { actor: 'diya',     x: 1.6,  y: -0.5,  z: 0,    ry: -0.4,  s: 1.25, rx: 0.2 },
  'diya-club':      { actor: 'diya',     x: 1.7,  y: -0.55, z: -0.4, ry: 0.5,   s: 1.15, rx: 0.15 },
  'banyan':         { actor: 'banyan',   x: 1.5,  y: -1.4,  z: 0,    ry: 0,     s: 1.3,  rx: 0.12 },
  'none':           { actor: null },
};

export function createStage(canvas, { onProgress, onReady } = {}) {
  const isMobile = () => window.innerWidth < 860;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- renderer ----------
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile() ? 1.5 : 1.75));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#040a1c');
  scene.fog = new THREE.Fog('#040a1c', 9, 22);

  const camera = new THREE.PerspectiveCamera(32, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(0, 0.2, 7);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;

  // ---------- backdrop: deep navy dome with a low saffron glow ----------
  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(40, 48, 24),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { uTime: { value: 0 }, uGlow: { value: 0.0 } },
      vertexShader: `varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `
        varying vec3 vP; uniform float uTime; uniform float uGlow;
        void main(){
          float h = vP.y;
          vec3 top = vec3(0.0015,0.004,0.016);
          vec3 mid = vec3(0.004,0.011,0.04);
          vec3 low = vec3(0.001,0.003,0.012);
          vec3 c = mix(low, mid, smoothstep(-0.35, 0.05, h));
          c = mix(c, top, smoothstep(0.1, 0.8, h));
          float horizon = exp(-pow((h + 0.06) * 7.0, 2.0));
          c += vec3(0.9,0.42,0.1) * horizon * (0.025 + 0.03 * uGlow);
          c += vec3(0.17,0.34,0.84) * pow(max(0.0, 1.0 - abs(vP.x + 0.6)), 6.0) * 0.015;
          gl_FragColor = vec4(c, 1.0);
        }`,
    })
  );
  scene.add(dome);

  // ---------- lights ----------
  scene.add(new THREE.AmbientLight('#203060', 0.6));
  const key = new THREE.DirectionalLight('#ffd7a0', 2.4);
  key.position.set(4, 5, 4);
  scene.add(key);
  const rim = new THREE.DirectionalLight(ROYAL, 3.0);
  rim.position.set(-5, 2, -4);
  scene.add(rim);
  const fill = new THREE.PointLight(SAFFRON, 6, 12, 2);
  fill.position.set(-2, -0.5, 3);
  scene.add(fill);

  // ---------- gold dust ----------
  const DUST = isMobile() ? 350 : 800;
  const dustGeo = new THREE.BufferGeometry();
  const dPos = new Float32Array(DUST * 3), dSeed = new Float32Array(DUST);
  for (let i = 0; i < DUST; i++) {
    dPos[i * 3] = (Math.random() - 0.5) * 16;
    dPos[i * 3 + 1] = Math.random() * 8 - 2;
    dPos[i * 3 + 2] = (Math.random() - 0.5) * 10 - 1;
    dSeed[i] = Math.random();
  }
  dustGeo.setAttribute('position', new THREE.BufferAttribute(dPos, 3));
  dustGeo.setAttribute('aSeed', new THREE.BufferAttribute(dSeed, 1));
  const dustMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uPR: { value: renderer.getPixelRatio() }, uScroll: { value: 0 } },
    vertexShader: `
      attribute float aSeed; uniform float uTime; uniform float uPR; uniform float uScroll; varying float vA;
      void main(){
        vec3 p = position;
        p.y = mod(p.y + uTime * (0.05 + aSeed * 0.12) - uScroll * 1.5 * (0.4 + aSeed), 8.0) - 2.0;
        p.x += sin(uTime * 0.3 + aSeed * 40.0) * 0.25;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = (1.2 + aSeed * 2.6) * uPR * (6.0 / -mv.z);
        vA = (0.25 + 0.75 * fract(aSeed * 13.7)) * (0.6 + 0.4 * sin(uTime * (0.8 + aSeed) + aSeed * 30.0));
      }`,
    fragmentShader: `
      varying float vA;
      void main(){ float d = length(gl_PointCoord - 0.5); float a = smoothstep(0.5, 0.0, d); gl_FragColor = vec4(1.0, 0.76, 0.38, a * vA * 0.7); }`,
  });
  scene.add(new THREE.Points(dustGeo, dustMat));

  // ---------- actors ----------
  const actors = {};
  function makeActor(name) {
    const root = new THREE.Group();     // positioned by state
    const inner = new THREE.Group();    // normalized model lives here
    root.add(inner);
    root.visible = false;
    scene.add(root);
    const a = { name, root, inner, vis: 0, target: 0, materials: [], parts: {}, spread: 0, dim: 1 };
    actors[name] = a;
    return a;
  }

  // Fit model to max dimension 2 with its base at y=0 (centered in x/z).
  function normalize(obj) {
    const box = new THREE.Box3().setFromObject(obj);
    const size = box.getSize(new THREE.Vector3());
    const s = 2 / Math.max(size.x, size.y, size.z);
    obj.scale.multiplyScalar(s);
    const box2 = new THREE.Box3().setFromObject(obj);
    const c = box2.getCenter(new THREE.Vector3());
    obj.position.x -= c.x; obj.position.z -= c.z; obj.position.y -= box2.min.y;
  }

  function collectMaterials(a) {
    const seen = new Set();
    a.inner.traverse((o) => {
      if (o.isMesh) {
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        mats.forEach((m) => {
          if (seen.has(m)) return;
          seen.add(m);
          m.transparent = true;
          m.userData.baseOpacity = m.opacity ?? 1;
          if (m.envMapIntensity !== undefined) m.envMapIntensity = 1.1;
          a.materials.push(m);
        });
      }
      if (o.name) a.parts[o.name] = o;
    });
  }

  // --- procedural fallbacks (also define the look if GLBs are missing) ---
  function bladeShape(w, h) {
    const s = new THREE.Shape();
    const r = w * 0.45;
    s.moveTo(0, h * 0.12);
    s.lineTo(0, h - w * 0.06);
    s.quadraticCurveTo(0, h, w * 0.06, h);
    s.lineTo(w - r, h);
    s.quadraticCurveTo(w, h, w, h - r);
    s.lineTo(w, h * 0.45);
    s.bezierCurveTo(w, h * 0.12, w * 0.55, 0, 0, h * 0.12);
    return s;
  }
  const fallbacks = {
    monolith() {
      const g = new THREE.Group();
      const mat = new THREE.MeshPhysicalMaterial({ color: '#1d46b8', metalness: 0.35, roughness: 0.22, clearcoat: 1, clearcoatRoughness: 0.15 });
      [[0, 0, 0.36, 1.25, 1], [0.32, 0.18, 0.36, 1.45, 2], [0.64, 0.36, 0.36, 1.65, 3]].forEach(([x, y, w, h, i]) => {
        const geo = new THREE.ExtrudeGeometry(bladeShape(w, h), { depth: 0.12, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 4, curveSegments: 32 });
        geo.translate(-w / 2, 0, -0.06);
        const m = new THREE.Mesh(geo, mat);
        m.name = `blade_${i}`;
        m.position.set(x - 0.32, y, -(i - 1) * 0.2);
        g.add(m);
      });
      return g;
    },
    shankha() {
      const pts = [];
      for (let i = 0; i <= 24; i++) { const t = i / 24; pts.push(new THREE.Vector2(Math.sin(t * Math.PI) * 0.45 * (1 - t * 0.6), t * 2)); }
      const m = new THREE.Mesh(new THREE.LatheGeometry(pts, 48), new THREE.MeshPhysicalMaterial({ color: '#f3ece0', roughness: 0.3, sheen: 1 }));
      m.rotation.z = Math.PI / 2; m.name = 'shankha';
      const g = new THREE.Group(); g.add(m); return g;
    },
    urli() {
      const g = new THREE.Group();
      const pts = [[0, 0], [0.3, 0], [0.32, 0.06], [0.5, 0.1], [0.85, 0.28], [1, 0.42], [0.98, 0.46], [0.94, 0.44]].map(([x, y]) => new THREE.Vector2(x, y));
      g.add(new THREE.Mesh(new THREE.LatheGeometry(pts, 64), new THREE.MeshStandardMaterial({ color: '#c9973a', metalness: 1, roughness: 0.28, side: THREE.DoubleSide })));
      const w = new THREE.Mesh(new THREE.CircleGeometry(0.9, 64), new THREE.MeshStandardMaterial({ color: '#0b1a3a', roughness: 0.05 }));
      w.rotation.x = -Math.PI / 2; w.position.y = 0.36; w.name = 'water'; g.add(w);
      for (let i = 1; i <= 5; i++) {
        const p = new THREE.Mesh(new THREE.SphereGeometry(0.09, 16, 8), new THREE.MeshStandardMaterial({ color: '#f39c12', roughness: 0.6 }));
        const an = i * 1.3; p.position.set(Math.cos(an) * 0.45, 0.38, Math.sin(an) * 0.45); p.scale.y = 0.5; p.name = `petal_${i}`; g.add(p);
      }
      return g;
    },
    diya() {
      const g = new THREE.Group();
      const body = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 24, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), new THREE.MeshStandardMaterial({ color: '#a4502a', roughness: 0.85, side: THREE.DoubleSide }));
      body.scale.set(1, 0.45, 0.75); body.rotation.x = Math.PI; body.position.y = 0.45; g.add(body);
      const anchor = new THREE.Object3D(); anchor.name = 'flame_anchor'; anchor.position.set(0.95, 0.5, 0); g.add(anchor);
      return g;
    },
    banyan() {
      const g = new THREE.Group();
      const bronze = new THREE.MeshStandardMaterial({ color: '#8a5a2b', metalness: 0.8, roughness: 0.4 });
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.18, 1, 12), bronze); trunk.position.y = 0.5; g.add(trunk);
      const can = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), new THREE.MeshStandardMaterial({ color: '#0f3b3a', roughness: 0.6 }));
      can.scale.set(1, 0.32, 0.8); can.position.y = 1.05; g.add(can);
      for (let i = 1; i <= 20; i++) {
        const n = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 8), new THREE.MeshStandardMaterial({ color: '#f2c14e' }));
        const t = i * 2.399, r = 0.25 + 0.7 * Math.sqrt(i / 20);
        n.position.set(Math.cos(t) * r, 1.05 + 0.3 * Math.sqrt(1 - (r * r)), Math.sin(t) * r * 0.8);
        n.name = `node_${String(i).padStart(2, '0')}`; g.add(n);
      }
      return g;
    },
  };

  // ---------- loading ----------
  const manager = new THREE.LoadingManager();
  const loader = new GLTFLoader(manager);
  const NAMES = ['monolith', 'shankha', 'urli', 'diya', 'banyan'];
  const FILES = { monolith: 'rrr_monolith', shankha: 'shankha', urli: 'urli', diya: 'diya', banyan: 'banyan' };
  let loaded = 0;

  const loadOne = (name) => new Promise((resolve) => {
    const a = makeActor(name);
    const done = (obj) => {
      a.inner.add(obj);
      normalize(obj);
      collectMaterials(a);
      setupActor(a);
      loaded++;
      onProgress?.(loaded / NAMES.length);
      resolve();
    };
    loader.load(`/models/${FILES[name]}.glb`, (gltf) => done(gltf.scene), undefined, () => {
      console.info(`[stage] using fallback for ${name}`);
      done(fallbacks[name]());
    });
  });

  // ---------- per-actor extras ----------
  const flame = { light: null, sprite: null };
  const rings = [];
  const ripples = [];
  let nodes = [];
  let nodeLit = 0;

  function ringMaterial() {
    return new THREE.MeshBasicMaterial({ color: SAFFRON, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  }

  function setupActor(a) {
    if (a.name === 'monolith') {
      ['blade_1', 'blade_2', 'blade_3'].forEach((n, i) => {
        const b = a.parts[n];
        if (b) { b.userData.base = b.position.clone(); b.userData.idx = i; }
      });
    }
    if (a.name === 'shankha') {
      // signal rings: "listening" to the market
      for (let i = 0; i < 4; i++) {
        const r = new THREE.Mesh(new THREE.TorusGeometry(1, 0.006, 8, 96), ringMaterial());
        r.userData.phase = i / 4;
        a.root.add(r);
        rings.push(r);
      }
    }
    if (a.name === 'urli') {
      const water = a.parts.water;
      const y = water ? new THREE.Box3().setFromObject(water).max.y : 0.4;
      for (let i = 0; i < 3; i++) {
        const r = new THREE.Mesh(new THREE.RingGeometry(0.98, 1, 96), ringMaterial());
        r.material.color = new THREE.Color('#f7d58b');
        r.rotation.x = -Math.PI / 2;
        r.position.y = (y - a.inner.position.y) / 1 + 0.004;
        r.userData.phase = i / 3;
        a.inner.add(r);
        ripples.push(r);
      }
      Object.keys(a.parts).filter((k) => k.startsWith('petal_')).forEach((k, i) => {
        const p = a.parts[k]; p.userData.base = p.position.clone(); p.userData.i = i;
      });
    }
    if (a.name === 'diya') {
      const anchor = a.parts.flame_anchor;
      const sprite = new THREE.Mesh(
        new THREE.PlaneGeometry(1, 1),
        new THREE.ShaderMaterial({
          transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
          uniforms: { uTime: { value: 0 }, uOpacity: { value: 0 } },
          vertexShader: `varying vec2 vUv; void main(){ vUv = uv; vec4 mv = modelViewMatrix * vec4(0.0,0.0,0.0,1.0); vec2 sc = vec2(length(modelMatrix[0].xyz), length(modelMatrix[1].xyz)); mv.xy += position.xy * sc; gl_Position = projectionMatrix * mv; }`,
          fragmentShader: `
            varying vec2 vUv; uniform float uTime; uniform float uOpacity;
            void main(){
              vec2 p = vUv - vec2(0.5, 0.18);
              float sway = sin(uTime * 7.0 + p.y * 6.0) * 0.03 * p.y + sin(uTime * 13.0) * 0.008;
              p.x += sway;
              float w = mix(0.17, 0.0, clamp(p.y / 0.72, 0.0, 1.0));
              w *= smoothstep(-0.1, 0.05, p.y);
              float d = abs(p.x) / max(w, 0.0001);
              float core = smoothstep(1.0, 0.0, d) * smoothstep(0.75, 0.0, p.y) * step(-0.12, p.y);
              float halo = exp(-length(p * vec2(1.6, 1.0)) * 5.0) * 0.35;
              vec3 col = mix(vec3(1.0, 0.45, 0.08), vec3(1.0, 0.92, 0.7), smoothstep(0.2, 1.0, core));
              gl_FragColor = vec4(col * (core * 1.6 + halo), (core + halo) * uOpacity);
            }`,
        })
      );
      sprite.scale.set(0.42, 0.62, 1);
      (anchor || a.inner).add(sprite);
      // counter the parent's scale so the flame stays a sensible size
      if (anchor) {
        const ws = new THREE.Vector3(); anchor.getWorldScale(ws);
        sprite.scale.set(0.42 / (ws.x || 1), 0.62 / (ws.y || 1), 1);
        sprite.position.y = (0.62 * 0.3) / (ws.y || 1);
      }
      const light = new THREE.PointLight('#ffb050', 0, 5, 1.6);
      (anchor || a.inner).add(light);
      flame.light = light; flame.sprite = sprite;
    }
    if (a.name === 'banyan') {
      nodes = Object.keys(a.parts).filter((k) => /^node_\d+/.test(k)).sort().map((k) => a.parts[k]);
      nodes.forEach((n) => {
        n.material = new THREE.MeshStandardMaterial({ color: '#3a2c10', emissive: GOLD, emissiveIntensity: 0, roughness: 0.4, metalness: 0.3, transparent: true });
        a.materials.push(n.material);
        n.userData.lit = 0;
      });
    }
  }

  // ---------- state ----------
  let current = 'monolith';
  let sectionProgress = 0;
  let scrollVel = 0;
  const mouse = new THREE.Vector2();
  const mouseLerp = new THREE.Vector2();

  function setState(name) {
    if (!STATES[name] || name === current) return;
    current = name;
    const st = STATES[name];
    for (const k in actors) actors[k].target = st.actor === k ? 1 : 0;
  }

  function stateFor(a) {
    const st = STATES[current];
    if (st.actor === a.name) return st;
    // when leaving, keep the last state this actor had
    return a.lastState || st;
  }

  function damp(cur, tgt, lambda, dt) { return THREE.MathUtils.damp(cur, tgt, lambda, dt); }

  // ---------- intro ----------
  let introT = 0; // 0..1, blades rise on first load
  let introStarted = false;

  // ---------- loop ----------
  const clock = new THREE.Clock();
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.42, 0.6, 0.92);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  function tick() {
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;
    const mobile = isMobile();

    if (introStarted) introT = Math.min(1, introT + dt / 2.2);

    mouseLerp.x = damp(mouseLerp.x, mouse.x, 3, dt);
    mouseLerp.y = damp(mouseLerp.y, mouse.y, 3, dt);
    camera.position.x = mouseLerp.x * 0.25;
    camera.position.y = 0.2 + mouseLerp.y * 0.15;
    camera.lookAt(0, -0.1, 0);

    dome.material.uniforms.uTime.value = t;
    dustMat.uniforms.uTime.value = t;
    dustMat.uniforms.uScroll.value = window.scrollY / window.innerHeight * 0.1;

    for (const k in actors) {
      const a = actors[k];
      const speed = a.target > a.vis ? 2.4 : 3.2;
      a.vis = damp(a.vis, a.target, speed, dt);
      if (a.target === 1) a.lastState = STATES[current];
      const st = stateFor(a);
      if (!st || !st.actor) { a.root.visible = a.vis > 0.003; continue; }
      a.root.visible = a.vis > 0.003;
      if (!a.root.visible) continue;

      // layout: on narrow screens the object sits centered above the text
      let x = st.x, y = st.y, s = st.s;
      if (mobile) { x = 0; y = 0.45 + (st.y + 1.55) * 0.3; s = st.s * 0.62; }

      const enter = 1 - a.vis;
      const tx = x, ty = y - enter * 0.6, tz = st.z || 0;
      a.root.position.x = damp(a.root.position.x, tx, 3.5, dt);
      a.root.position.y = damp(a.root.position.y, ty, 3.5, dt);
      a.root.position.z = damp(a.root.position.z, tz, 3.5, dt);
      const sc = s * (0.88 + 0.12 * a.vis);
      a.root.scale.setScalar(damp(a.root.scale.x || sc, sc, 3.5, dt));

      const scrollSpin = (a.target === 1 ? sectionProgress : 0) * 0.9;
      const idle = reduced ? 0 : Math.sin(t * 0.35) * 0.08;
      const ry = (st.ry || 0) + scrollSpin + idle + mouseLerp.x * 0.15;
      a.root.rotation.y = damp(a.root.rotation.y, ry, 3, dt);
      a.root.rotation.x = damp(a.root.rotation.x, (st.rx || 0) - mouseLerp.y * 0.05, 3, dt);

      a.dim = damp(a.dim, st.dim ?? 1, 3, dt);
      const op = a.vis * a.dim;
      a.materials.forEach((m) => { m.opacity = (m.userData.baseOpacity ?? 1) * op; m.depthWrite = op > 0.9; });

      // actor specifics
      if (a.name === 'monolith') {
        a.spread = damp(a.spread, st.spread || 0, 2.5, dt);
        ['blade_1', 'blade_2', 'blade_3'].forEach((n, i) => {
          const b = a.parts[n]; if (!b || !b.userData.base) return;
          const base = b.userData.base;
          const off = (i - 1);
          const rise = THREE.MathUtils.smoothstep(introT * 1.6 - i * 0.25, 0, 1);
          b.position.x = base.x + off * a.spread * 0.55;
          b.position.y = base.y - (1 - rise) * 2.2 + (reduced ? 0 : Math.sin(t * 0.8 + i) * 0.015);
          b.position.z = base.z + Math.abs(off) * a.spread * -0.2;
          b.rotation.y = off * a.spread * 0.35;
        });
      }
      if (a.name === 'shankha') {
        a.root.position.y += reduced ? 0 : Math.sin(t * 0.9) * 0.002;
        rings.forEach((r) => {
          const p = (t * 0.25 + r.userData.phase) % 1;
          const rs = 0.35 + p * 0.9;
          r.scale.setScalar(rs);
          r.position.set(0, 0.5, 0);
          r.rotation.set(0, -a.root.rotation.y, 0);
          r.material.opacity = Math.sin(p * Math.PI) * 0.28 * op;
        });
      }
      if (a.name === 'urli') {
        ripples.forEach((r) => {
          const p = (t * 0.18 + r.userData.phase) % 1;
          const rs = 0.1 + p * 0.8;
          r.scale.setScalar(rs);
          r.material.opacity = Math.sin(p * Math.PI) * 0.35 * op;
        });
        Object.values(a.parts).forEach((p) => {
          if (!p.userData.base) return;
          const i = p.userData.i;
          p.position.y = p.userData.base.y + (reduced ? 0 : Math.sin(t * 1.2 + i * 1.7) * 0.004);
          p.rotation.y = t * 0.05 * (i % 2 ? 1 : -1);
        });
      }
      if (a.name === 'diya' && flame.sprite) {
        flame.sprite.material.uniforms.uTime.value = t;
        flame.sprite.material.uniforms.uOpacity.value = a.vis;
        const flick = 0.85 + Math.sin(t * 11) * 0.06 + Math.sin(t * 23.0) * 0.05 + Math.random() * 0.04;
        flame.light.intensity = 3.5 * flick * a.vis;
      }
      if (a.name === 'banyan') {
        const target = a.target === 1 ? Math.round(THREE.MathUtils.clamp(sectionProgress * 1.35, 0, 1) * nodes.length) : nodeLit;
        nodeLit = target;
        nodes.forEach((n, i) => {
          const on = i < nodeLit ? 1 : 0;
          n.userData.lit = damp(n.userData.lit, on, 4, dt);
          n.material.emissiveIntensity = n.userData.lit * (2.2 + Math.sin(t * 2 + i) * 0.4) + 0.05;
        });
      }
    }

    // a warm glow on the horizon when the diya is lit
    dome.material.uniforms.uGlow.value = actors.diya ? actors.diya.vis : 0;

    composer.render();
    requestAnimationFrame(tick);
  }

  function onResize() {
    const w = window.innerWidth, h = window.innerHeight;
    camera.aspect = w / h;
    // keep objects comfortably framed on tall screens
    camera.fov = w / h < 0.8 ? 44 : 32;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile() ? 1.5 : 1.75));
    renderer.setSize(w, h);
    composer.setSize(w, h);
    dustMat.uniforms.uPR.value = renderer.getPixelRatio();
  }
  window.addEventListener('resize', onResize);
  window.addEventListener('pointermove', (e) => {
    mouse.set((e.clientX / window.innerWidth) * 2 - 1, -((e.clientY / window.innerHeight) * 2 - 1));
  }, { passive: true });

  if (import.meta.env.DEV) window.__stage = { scene, dome, bloom, renderer };
  onResize();
  Promise.all(NAMES.map(loadOne)).then(() => {
    actors.monolith.target = 1;
    actors.monolith.vis = 0.0;
    onReady?.();
  });
  requestAnimationFrame(tick);

  return {
    setState,
    setProgress(p) { sectionProgress = p; },
    startIntro() { introStarted = true; },
    get nodeLit() { return nodeLit; },
    get nodeTotal() { return nodes.length; },
  };
}
