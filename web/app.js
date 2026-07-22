import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const summaryEl = document.getElementById("summary");
const findingsEl = document.getElementById("findings");
const actionsEl = document.getElementById("actions");
const narrativeEl = document.getElementById("narrative");
const ruleDescEl = document.getElementById("rule-desc");
const btnSample = document.getElementById("btn-sample");
const btnFloor = document.getElementById("btn-floor");
const btnOverview = document.getElementById("btn-overview");
const floorNavEl = document.getElementById("floor-nav");
const fileInput = document.getElementById("file-input");
const labelsEl = document.getElementById("labels");
const floorBadgeEl = document.getElementById("floor-badge");
const canvasEl = document.getElementById("c");
const explainModeEl = document.getElementById("explain-mode");

const CW = 2.6;
const CL = 22.0;
const WH = 2.85;
const WT = 0.15;
const UNIT_W = 3.0;
const CORE_W = 2.6;
const BW = -UNIT_W;
const BE = CW + CORE_W;
const BAND = WH + 0.15;
const ACTIVE = 23;
const TOTAL_FLOORS = 28;
const FLOOR_START = 1;
const TOWER_CZ = CL / 2;
const TOWER_CX = (BW + BE) / 2;

const renderer = new THREE.WebGLRenderer({ canvas: canvasEl, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.98;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xb8c8d8, 55, 165);

const camera = new THREE.PerspectiveCamera(48, 1, 0.5, 400);

let composer = null;
let envMap = null;

const controls = new OrbitControls(camera, canvasEl);
controls.enableDamping = true;
controls.dampingFactor = 0.12;
controls.maxPolarAngle = Math.PI;
controls.minPolarAngle = 0;
controls.enablePan = true;
controls.enableZoom = false; // custom linear wheel zoom below — OrbitControls zoom feels exponential/floaty
controls.rotateSpeed = 0.55;
controls.panSpeed = 0.7;
controls.screenSpacePanning = true;
controls.update();

let orbitMode = "overview";
let zoomStep = 2.0;

/** Keep zoom gentle in corridor detail; only allow far pullback in overview. */
function setOrbitLimits(mode = "overview") {
  orbitMode = mode;
  if (mode === "detail") {
    controls.minDistance = 1.4;
    controls.maxDistance = 8;
    zoomStep = 0.28;
  } else if (mode === "floor") {
    controls.minDistance = 2.5;
    controls.maxDistance = 22;
    zoomStep = 0.55;
  } else {
    controls.minDistance = 12;
    controls.maxDistance = 160;
    zoomStep = 2.2;
  }
}
setOrbitLimits("overview");

function stopFlyAnim() {
  flyAnim = null;
}

function applyLinearZoom(deltaY) {
  stopFlyAnim();
  const direction = Math.sign(deltaY);
  if (!direction) return;
  const offset = camera.position.clone().sub(controls.target);
  const distance = offset.length();
  if (distance < 1e-4) return;
  const next = THREE.MathUtils.clamp(
    distance + direction * zoomStep,
    controls.minDistance,
    controls.maxDistance
  );
  offset.setLength(next);
  camera.position.copy(controls.target).add(offset);
  controls.update();
}

canvasEl.addEventListener("pointerdown", stopFlyAnim);
canvasEl.addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    // Normalize mouse / trackpad: take one step per event for stability
    applyLinearZoom(event.deltaY);
  },
  { passive: false }
);
canvasEl.addEventListener("touchstart", stopFlyAnim, { passive: true });

scene.add(new THREE.HemisphereLight(0xf4f8ff, 0x6a7868, 0.42));
const key = new THREE.DirectionalLight(0xfffaf4, 0.92);
key.position.set(18, 42, 24);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 4;
key.shadow.camera.far = 160;
key.shadow.camera.left = -40;
key.shadow.camera.right = 40;
key.shadow.camera.top = 55;
key.shadow.camera.bottom = -5;
key.shadow.bias = -0.0003;
key.shadow.normalBias = 0.02;
scene.add(key);
const fill = new THREE.DirectionalLight(0xc8dcff, 0.28);
fill.position.set(-16, 22, 18);
scene.add(fill);
const rim = new THREE.DirectionalLight(0x90b8ff, 0.22);
rim.position.set(-20, 30, -16);
scene.add(rim);

let cityRoot = null;
let buildingRoot = null;
let skyMesh = null;
let markerMap = new Map();
let labelDefs = [];
let pulseMeshes = [];
let animClock = 0;
let flyAnim = null;
let focusedId = null;

function floorY(floor) {
  return (floor - 1) * BAND;
}

function towerCenterY(floor = ACTIVE) {
  return floorY(floor) + WH * 0.5;
}

function canvasTex(drawFn, w = 256, h = 256) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  drawFn(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function tileTexture(base, alt) {
  return canvasTex((g, s) => {
    g.fillStyle = base;
    g.fillRect(0, 0, s, s);
    g.fillStyle = alt;
    for (let i = 0; i < s; i += 32) {
      for (let j = 0; j < s; j += 32) {
        if ((i / 32 + j / 32) % 2) g.fillRect(i, j, 32, 32);
      }
    }
  });
}

function setupEnvMap() {
  if (envMap) envMap.dispose();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envScene = new THREE.Scene();
  envScene.background = new THREE.Color(0xb8d0e8);
  envScene.add(new THREE.HemisphereLight(0xffffff, 0x889888, 1));
  const g1 = new THREE.Mesh(new THREE.SphereGeometry(2, 16, 16), new THREE.MeshBasicMaterial({ color: 0xffffff }));
  g1.position.set(5, 8, 3);
  envScene.add(g1);
  const g2 = new THREE.Mesh(new THREE.SphereGeometry(3, 16, 16), new THREE.MeshBasicMaterial({ color: 0x88aacc }));
  g2.position.set(-4, 2, -2);
  envScene.add(g2);
  envMap = pmrem.fromScene(envScene, 0.04).texture;
  pmrem.dispose();
}

let bloomPass = null;

function setupPostProcessing() {
  composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  bloomPass = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.12, 0.35, 0.92);
  composer.addPass(bloomPass);
  const fxaa = new ShaderPass(FXAAShader);
  composer.addPass(fxaa);
  composer.addPass(new OutputPass());
}

function hkFacadeTexture(seed = 0) {
  return canvasTex((g, w, h) => {
    g.fillStyle = "#e6dfd4";
    g.fillRect(0, 0, w, h);
    const rows = 14;
    const cols = 5;
    for (let row = 0; row < rows; row++) {
      const band = row % 4 === 0;
      if (band) {
        g.fillStyle = "#d8d0c4";
        g.fillRect(0, (h / rows) * row, w, h / rows * 0.35);
      }
      for (let col = 0; col < cols; col++) {
        const lit = ((row * 7 + col * 3 + seed) % 5) > 1;
        const x = 8 + col * ((w - 16) / cols);
        const y = 6 + row * ((h - 12) / rows);
        g.fillStyle = lit ? "#3a5878" : "#1a2838";
        g.fillRect(x, y, 14, 18);
        g.fillStyle = "rgba(180,210,240,0.25)";
        g.fillRect(x + 1, y + 1, 5, 14);
      }
    }
  }, 128, 512);
}

function buildSolidTowerSection(group, yBase, height, seed = 0) {
  const fTex = hkFacadeTexture(seed);
  fTex.repeat.set(1.2, height / 6);
  const m = mat(0xffffff, { map: fTex, roughness: 0.42, metalness: 0.14, envMap, envMapIntensity: 0.35 });
  box(group, BE - BW + 0.12, height, CL + 0.5, TOWER_CX, yBase + height / 2, TOWER_CZ, m, `TowerSolid-${yBase}`);
}

function buildSectionCutFrames(group, yLow, yHigh) {
  const slabMat = mat(0xe8e4de, { roughness: 0.65, metalness: 0.08 });
  for (const y of [yLow, yHigh]) {
    box(group, BE - BW + 0.2, 0.14, CL + 0.2, TOWER_CX, y + 0.07, TOWER_CZ, slabMat, `CutSlab-${y}`);
  }
}

function buildSouthGallery(group, dy) {
  const glass = mat(0xa8cce8, { transparent: true, opacity: 0.28, metalness: 0.55, roughness: 0.06, envMap, envMapIntensity: 0.65 });
  const frame = mat(0xd8d4cc, { metalness: 0.4, roughness: 0.35, envMap, envMapIntensity: 0.35 });
  const z = TOWER_CZ - CL / 2 - 0.04;
  box(group, BE - BW + 0.3, WH, 0.06, TOWER_CX, dy + WH / 2, z, glass, "SouthGlass");
  box(group, BE - BW + 0.35, 0.1, 0.1, TOWER_CX, dy + WH - 0.05, z, frame, "SouthFrame-T");
  box(group, BE - BW + 0.35, 0.1, 0.1, TOWER_CX, dy + 0.05, z, frame, "SouthFrame-B");
  box(group, 0.08, WH, 0.1, BW - 0.02, dy + WH / 2, z, frame, "SouthFrame-L");
  box(group, 0.08, WH, 0.1, BE + 0.02, dy + WH / 2, z, frame, "SouthFrame-R");
}

function buildUnitRoom(group, dy, doorZ, index) {
  const cz = TOWER_CZ + doorZ - CL / 2;
  const mWall = mat(0xf0ece6, { roughness: 0.85 });
  const mFloor = mat(0xe0d8cc, { roughness: 0.88 });
  const mFurn = mat(0x9a8878, { roughness: 0.82 });
  const depth = UNIT_W - 0.15;
  const cx = BW + depth / 2;

  box(group, depth, 0.08, 2.4, cx, dy + 0.04, cz, mFloor, `UnitFloor-${index}`);
  box(group, WT, WH, 2.4, BW + WT / 2, dy + WH / 2, cz, mWall, `UnitWall-W-${index}`);
  box(group, depth, WH, WT, cx, dy + WH / 2, cz - 1.2, mWall, `UnitWall-S-${index}`);
  box(group, depth, WH, WT, cx, dy + WH / 2, cz + 1.2, mWall, `UnitWall-N-${index}`);
  box(group, 0.08, WH, 2.2, BW + depth - 0.04, dy + WH / 2, cz, mWall, `UnitWall-E-${index}`);
  box(group, 0.06, 2.05, 0.78, -0.02, dy + 1.05, cz, mat(0x7a5c42, { roughness: 0.85 }), `UnitDoor-${index}`);
  box(group, 0.8, 0.06, 1.2, cx - 0.3, dy + 0.5, cz - 0.3, mFurn, `UnitSofa-${index}`);
  box(group, 0.5, 0.75, 0.4, cx + 0.4, dy + 0.42, cz + 0.5, mat(0xe8e4dc, { roughness: 0.9 }), `UnitCab-${index}`);
}

function buildStairwell(group, dy, door, isFail) {
  const doorZ = door.location.y;
  const cz = TOWER_CZ + doorZ - CL / 2;
  const w = door.clear_width_mm / 1000;
  const swZ = 2.6;
  const swX = (CW + BE) / 2;
  const swDepth = BE - CW - 0.05;
  const mCore = mat(0xd0d4da, { roughness: 0.72, metalness: 0.1, envMap, envMapIntensity: 0.18 });
  const mStair = mat(0xa8acb0, { roughness: 0.78 });
  const mLanding = mat(0xd8d0c4, { roughness: 0.9 });

  box(group, swDepth, 0.1, swZ, swX, dy + 0.05, cz, mLanding, `${door.id}-landing`);
  box(group, WT, WH, swZ, BE - WT / 2, dy + WH / 2, cz, mCore, `${door.id}-wall-out`);
  box(group, swDepth, WH, WT, swX, dy + WH / 2, cz - swZ / 2, mCore, `${door.id}-wall-s`);
  box(group, swDepth, WH, WT, swX, dy + WH / 2, cz + swZ / 2, mCore, `${door.id}-wall-n`);
  box(group, WT, WH, swZ, CW + WT / 2, dy + WH / 2, cz, mCore, `${door.id}-wall-in`);

  const openingW = Math.max(w, 0.82);
  const wallFaceX = CW;
  const doorThickness = 0.055;
  const doorX = wallFaceX - doorThickness / 2 - 0.02;
  const frameX = wallFaceX + 0.025;
  const frameDepth = 0.05;

  for (let i = 0; i < 8; i++) {
    box(group, 0.22, 0.17, 0.38, CW + 0.45 + i * 0.2, dy + 0.14 + i * 0.17, cz - 0.55 + i * 0.12, mStair, `${door.id}-step-${i}`);
  }
  box(group, 0.04, 0.9, swZ - 0.2, CW + 0.35, dy + 0.55, cz, mat(0x808890, { metalness: 0.4 }), `${door.id}-rail`);

  const dc = isFail ? 0xc03028 : 0x2a7d52;
  const doorMat = mat(dc, {
    emissive: isFail ? 0x401010 : 0x000000,
    emissiveIntensity: isFail ? 0.22 : 0,
    roughness: 0.5,
    metalness: 0.18,
  });
  doorMat.polygonOffset = true;
  doorMat.polygonOffsetFactor = -2;
  doorMat.polygonOffsetUnits = -2;
  box(group, doorThickness, 2.05, openingW - 0.04, doorX, dy + 1.05, cz, doorMat, door.id);
  const frameMat = mat(0x3a3a3a, { metalness: 0.35 });
  box(group, frameDepth, 2.12, 0.06, frameX, dy + 1.1, cz - openingW / 2 - 0.03, frameMat, `${door.id}-frame-l`);
  box(group, frameDepth, 2.12, 0.06, frameX, dy + 1.1, cz + openingW / 2 + 0.03, frameMat, `${door.id}-frame-r`);
  box(group, frameDepth, 0.06, openingW + 0.12, frameX, dy + 2.12, cz, frameMat, `${door.id}-frame-t`);
  box(group, 0.28, 0.1, 0.16, doorX - 0.04, dy + 2.35, cz,
    mat(isFail ? 0xdd3333 : 0x22aa55, { emissive: isFail ? 0x401010 : 0x002208, emissiveIntensity: 0.25 }), `${door.id}-sign`);

  const doorY = dy + 1.15;
  registerMarker(
    door.id,
    doorX,
    doorY,
    cz,
    `${door.id} · ${door.clear_width_mm}mm${isFail ? "" : " ✓"}`,
    isFail ? "fail" : "ok"
  );
  if (isFail) {
    addFailMarker(group, doorX, doorY + 0.05, cz);
  }
}

function buildLiftLobby(group, dy) {
  const cz = TOWER_CZ + 11 - CL / 2;
  const lx = (CW + BE) / 2;
  const mCore = mat(0xc8ccd2, { roughness: 0.65, metalness: 0.12, envMap, envMapIntensity: 0.2 });
  box(group, BE - CW - 0.1, WH - 0.1, 3.8, lx, dy + WH / 2, cz, mCore, "LiftLobby");
  box(group, BE - CW - 0.1, 0.08, 3.8, lx, dy + 0.04, cz, mat(0xd0ccc4, { roughness: 0.88 }), "LiftLobbyFloor");
  [-1.05, 0, 1.05].forEach((o, i) => {
    box(group, 0.12, 2.55, 0.95, lx - 0.15, dy + 1.3, cz + o, mat(0x909498, { metalness: 0.3, roughness: 0.5 }), `Lift-${i + 1}`);
    box(group, 0.02, 2.5, 0.88, lx + 0.2, dy + 1.28, cz + o, mat(0x707480, { metalness: 0.45 }), `LiftDoor-${i + 1}`);
  });
}

function buildTree(parent, x, z, scale = 1) {
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.07 * scale, 0.1 * scale, 1.0 * scale, 8),
    mat(0x5a4030, { roughness: 0.92 }));
  trunk.position.y = 0.5 * scale;
  g.add(trunk);
  [[0, 1.15], [-0.25, 1.0], [0.22, 0.95]].forEach(([ox, oy], i) => {
    const fol = new THREE.Mesh(new THREE.SphereGeometry(0.42 * scale, 10, 10), mat(i === 0 ? 0x3a7040 : 0x448848, { roughness: 0.9 }));
    fol.position.set(ox * scale, oy * scale, 0);
    fol.castShadow = true;
    g.add(fol);
  });
  g.position.set(x, 0, z);
  parent.add(g);
}

function cardboardTexture() {
  return canvasTex((g, w, h) => {
    g.fillStyle = "#c4a574";
    g.fillRect(0, 0, w, h);
    g.strokeStyle = "#a88858";
    for (let i = 0; i < 8; i++) {
      g.beginPath();
      g.moveTo(Math.random() * w, 0);
      g.lineTo(Math.random() * w, h);
      g.stroke();
    }
    g.fillStyle = "#8a7050";
    g.fillRect(0, h * 0.45, w, 6);
    g.fillRect(w * 0.4, 0, 8, h);
  }, 128, 128);
}

function mat(color, opts = {}) {
  const m = new THREE.MeshStandardMaterial({
    color,
    roughness: opts.roughness ?? 0.72,
    metalness: opts.metalness ?? 0.08,
    transparent: opts.transparent ?? false,
    opacity: opts.opacity ?? 1,
    emissive: opts.emissive ?? 0x000000,
    emissiveIntensity: opts.emissiveIntensity ?? 0,
    map: opts.map ?? null,
  });
  if (opts.envMap) {
    m.envMap = opts.envMap;
    m.envMapIntensity = opts.envMapIntensity ?? 0.3;
  }
  return m;
}

function addMesh(group, geo, material, x, y, z, name, castShadow = true) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(x, y, z);
  m.name = name;
  m.castShadow = castShadow;
  m.receiveShadow = true;
  group.add(m);
  return m;
}

function box(group, sx, sy, sz, x, y, z, material, name) {
  return addMesh(group, new THREE.BoxGeometry(sx, sy, sz), material, x, y, z, name);
}

function aabbCenter(aabb) {
  return [(aabb.min[0] + aabb.max[0]) / 2, (aabb.min[1] + aabb.max[1]) / 2];
}

function aabbSize(aabb) {
  return [aabb.max[0] - aabb.min[0], aabb.max[1] - aabb.min[1]];
}

function registerMarker(id, x, y, z, label, kind = "fail") {
  markerMap.set(id, new THREE.Vector3(x, y, z));
  labelDefs.push({ id, label, kind });
}

function addFailMarker(group, x, y, z) {
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.14, 0.22, 32),
    mat(0xff5533, { emissive: 0xff3311, emissiveIntensity: 0.55, transparent: true, opacity: 0.88, side: THREE.DoubleSide })
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.set(x, y, z);
  group.add(ring);
  pulseMeshes.push(ring);
  const pin = new THREE.Mesh(
    new THREE.CylinderGeometry(0.025, 0.025, 0.55, 12),
    mat(0xff6644, { emissive: 0xff2200, emissiveIntensity: 0.35, roughness: 0.4 })
  );
  pin.position.set(x, y + 0.28, z);
  group.add(pin);
  return ring;
}

function buildSky() {
  if (skyMesh) {
    scene.remove(skyMesh);
    skyMesh.geometry.dispose();
    skyMesh.material.dispose();
  }
  const tex = canvasTex((g, w, h) => {
    const grad = g.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, "#4a78a8");
    grad.addColorStop(0.18, "#7aa8cc");
    grad.addColorStop(0.45, "#a8c8dc");
    grad.addColorStop(0.72, "#d0e0ec");
    grad.addColorStop(1, "#e8eef2");
    g.fillStyle = grad;
    g.fillRect(0, 0, w, h);
    g.fillStyle = "rgba(255,255,255,0.35)";
    for (let i = 0; i < 10; i++) {
      g.beginPath();
      g.ellipse(60 + i * 90, h * (0.05 + (i % 3) * 0.03), 50 + (i % 4) * 15, 9 + (i % 2) * 5, 0, 0, Math.PI * 2);
      g.fill();
    }
    g.fillStyle = "rgba(180,200,220,0.25)";
    g.fillRect(0, h * 0.72, w, h * 0.28);
  }, 2048, 1024);
  skyMesh = new THREE.Mesh(
    new THREE.SphereGeometry(220, 48, 24),
    new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, fog: false })
  );
  skyMesh.position.set(TOWER_CX, 45, TOWER_CZ);
  scene.add(skyMesh);
}

function buildSurroundingTower(parent, x, z, h, w, d, seed) {
  const g = new THREE.Group();
  g.position.set(x, 0, z);
  const podH = 2.2 + (seed % 3) * 0.6;
  const podTex = canvasTex((ctx, pw, ph) => {
    ctx.fillStyle = "#8a8880";
    ctx.fillRect(0, 0, pw, ph);
    for (let i = 0; i < pw; i += 20) {
      ctx.strokeStyle = "#7a7870";
      ctx.strokeRect(i, 0, 18, ph);
    }
  }, 64, 32);
  box(g, w + 0.6, podH, d + 0.6, 0, podH / 2, 0, mat(0xffffff, { map: podTex, roughness: 0.78 }), "Podium");
  const fTex = hkFacadeTexture(seed);
  fTex.repeat.set(Math.max(1, w / 4), h / 5.5);
  const towerH = h - podH;
  box(g, w, towerH, d, 0, podH + towerH / 2, 0,
    mat(0xffffff, { map: fTex, roughness: 0.4, metalness: 0.14, envMap, envMapIntensity: 0.3 }), "Tower");
  box(g, w * 0.65, 0.25, d * 0.5, 0, h + 0.12, 0, mat(0x687078, { roughness: 0.55, metalness: 0.15 }), "Roof");
  if (seed % 2 === 0) {
    box(g, w * 0.3, 0.5, d * 0.25, w * 0.2, h + 0.35, d * 0.15, mat(0x606870), "RoofPlant");
  }
  parent.add(g);
}

function buildStreetLamp(parent, x, z) {
  const g = new THREE.Group();
  box(g, 0.08, 3.2, 0.08, 0, 1.6, 0, mat(0x505860, { metalness: 0.5, roughness: 0.4 }), "pole");
  box(g, 0.5, 0.06, 0.12, 0.2, 3.15, 0, mat(0x404850, { metalness: 0.45 }), "arm");
  const bulb = new THREE.PointLight(0xfff0d8, 0.08, 8);
  bulb.position.set(0.35, 3.0, 0);
  g.add(bulb);
  g.position.set(x, 0, z);
  parent.add(g);
}

function buildParkedCar(parent, x, z, rot = 0) {
  const g = new THREE.Group();
  const carCol = [0x2a3038, 0x4a5058, 0x606870, 0x3a4858][Math.abs(Math.floor(x + z)) % 4];
  box(g, 1.8, 0.5, 0.95, 0, 0.28, 0, mat(carCol, { metalness: 0.35, roughness: 0.45, envMap, envMapIntensity: 0.4 }), "body");
  box(g, 1.0, 0.38, 0.85, -0.1, 0.62, 0, mat(0x88aacc, { transparent: true, opacity: 0.45, metalness: 0.6, roughness: 0.1 }), "glass");
  g.rotation.y = rot;
  g.position.set(x, 0, z);
  parent.add(g);
}

function buildStroller(group, cx, cz, dy, isFail) {
  const g = new THREE.Group();
  g.name = "F-STROLLER-01";
  const frameCol = isFail ? 0x3a4550 : 0x4a5568;
  const fabricCol = isFail ? 0xe85820 : 0x556070;
  const mFrame = mat(frameCol, { metalness: 0.35, roughness: 0.45 });
  const mFabric = mat(fabricCol, { roughness: 0.88 });

  box(g, 0.52, 0.06, 0.82, 0, 0.28, 0, mFrame, "st-frame");
  box(g, 0.48, 0.22, 0.42, 0, 0.52, -0.08, mFabric, "st-seat");
  box(g, 0.44, 0.28, 0.38, 0, 0.78, -0.22, mFabric, "st-back");
  box(g, 0.46, 0.04, 0.36, 0, 1.02, -0.38, mat(0x2a3540, { roughness: 0.9 }), "st-hood");
  [[-0.2, -0.28], [0.2, -0.28], [-0.2, 0.28], [0.2, 0.28]].forEach(([wx, wz], i) => {
    const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.05, 16), mFrame);
    wheel.rotation.z = Math.PI / 2;
    wheel.position.set(wx, 0.09, wz);
    wheel.name = `st-wheel-${i}`;
    g.add(wheel);
  });
  box(g, 0.04, 0.7, 0.04, -0.18, 0.55, -0.05, mFrame, "st-handle-l");
  box(g, 0.04, 0.7, 0.04, 0.18, 0.55, -0.05, mFrame, "st-handle-r");
  box(g, 0.36, 0.04, 0.04, 0, 0.92, -0.05, mFrame, "st-handle-bar");

  g.position.set(cx, dy, cz);
  group.add(g);
  if (isFail) {
    pulseMeshes.push(g.children[1]);
    addFailMarker(group, cx, dy + 0.9, cz);
    registerMarker("F-STROLLER-01", cx, dy + 0.85, cz, "Stroller · blocks egress zone", "warn");
  }
  return g;
}

function buildCartonStack(group, cx, cz, dy, sx, sz, isFail) {
  const g = new THREE.Group();
  g.name = "F-CARTON-01";
  const ctex = cardboardTexture();
  const mBox = mat(0xffffff, { map: ctex, roughness: 0.92 });
  ctex.repeat.set(1.2, 1.2);

  const layouts = [
    [0, 0, sx * 0.92, 0.42, sz * 0.88],
    [-0.08, 0.42, sx * 0.55, 0.36, sz * 0.62],
    [0.1, 0.42, sx * 0.48, 0.34, sz * 0.55],
    [0, 0.76, sx * 0.72, 0.28, sz * 0.72],
  ];
  layouts.forEach(([ox, oy, w, h, d], i) => {
    box(g, w, h, d, ox, oy + h / 2, 0, mBox, `carton-${i}`);
    box(g, w * 0.95, 0.025, 0.07, ox, oy + h - 0.01, d * 0.48, mat(0x6a5840, { roughness: 0.95 }), `tape-${i}`);
  });
  g.rotation.y = 0.18;
  g.position.set(cx, dy, cz);
  group.add(g);
  if (isFail) {
    pulseMeshes.push(g.children[0]);
    addFailMarker(group, cx, dy + 0.75, cz);
    registerMarker("F-CARTON-01", cx, dy + 0.7, cz, "Cartons · obstruction", "warn");
  }
  return g;
}

function buildCityContext() {
  if (cityRoot) {
    scene.remove(cityRoot);
    cityRoot.traverse(disposeObject);
  }
  cityRoot = new THREE.Group();
  cityRoot.name = "City";
  const TOWER_H = floorY(TOTAL_FLOORS) + WH;

  const plazaTex = canvasTex((g, w, h) => {
    g.fillStyle = "#b8b4ac";
    g.fillRect(0, 0, w, h);
    for (let i = 0; i < 600; i++) {
      g.fillStyle = `rgba(0,0,0,${Math.random() * 0.04})`;
      g.fillRect(Math.random() * w, Math.random() * h, 2, 1);
    }
  }, 256, 256);
  plazaTex.repeat.set(16, 16);
  const plaza = new THREE.Mesh(new THREE.PlaneGeometry(280, 280),
    mat(0xffffff, { map: plazaTex, roughness: 0.88 }));
  plaza.rotation.x = -Math.PI / 2;
  plaza.position.set(TOWER_CX, 0, TOWER_CZ);
  plaza.receiveShadow = true;
  cityRoot.add(plaza);

  const parkTex = tileTexture("#6a8860", "#5a7858");
  parkTex.repeat.set(8, 8);
  [[-55, 55, 40, 35], [50, -50, 38, 32], [-60, -45, 35, 30]].forEach(([px, pz, pw, pd]) => {
    const park = new THREE.Mesh(new THREE.PlaneGeometry(pw, pd), mat(0xffffff, { map: parkTex, roughness: 0.95 }));
    park.rotation.x = -Math.PI / 2;
    park.position.set(TOWER_CX + px, 0.01, TOWER_CZ + pz);
    cityRoot.add(park);
  });

  const asphaltTex = canvasTex((g, w, h) => {
    g.fillStyle = "#3a3a40";
    g.fillRect(0, 0, w, h);
    for (let i = 0; i < 500; i++) {
      g.fillStyle = `rgba(255,255,255,${Math.random() * 0.035})`;
      g.fillRect(Math.random() * w, Math.random() * h, 1, 1);
    }
  }, 128, 128);
  asphaltTex.repeat.set(4, 4);
  const roadMat = mat(0xffffff, { map: asphaltTex, roughness: 0.9 });
  const sw = mat(0xc8c4bc, { roughness: 0.86 });
  for (let i = -2; i <= 2; i++) {
    const off = i * 22;
    box(cityRoot, 8, 0.08, 160, TOWER_CX + 14 + i * 3, 0.04, TOWER_CZ + off, roadMat, `Road-NS-${i}`);
    box(cityRoot, 1.4, 0.06, 160, TOWER_CX + 14 + i * 3 + 4.8, 0.05, TOWER_CZ + off, sw, `Sw-NS-${i}`);
    box(cityRoot, 160, 0.08, 8, TOWER_CX + off, 0.04, TOWER_CZ + 14 + i * 3, roadMat, `Road-EW-${i}`);
    box(cityRoot, 160, 0.06, 1.4, TOWER_CX + off, 0.05, TOWER_CZ + 14 + i * 3 + 4.8, sw, `Sw-EW-${i}`);
  }

  const ringSlots = [
    [-20, 14], [-22, -12], [20, -14], [22, 16], [-28, 2], [28, 4],
    [-14, 26], [16, 28], [-16, -26], [14, -28], [-32, 20], [30, -20],
    [-10, -32], [10, 32], [-34, -10], [32, 12],
  ];
  ringSlots.forEach(([bx, bz], i) => {
    const h = TOWER_H * (0.88 + (i % 4) * 0.04);
    const w = 8 + (i % 3) * 1.2;
    const d = 8 + ((i + 1) % 3) * 1.2;
    buildSurroundingTower(cityRoot, TOWER_CX + bx, TOWER_CZ + bz, h, w, d, i + 1);
  });

  for (let i = 0; i < 24; i++) {
    const a = (i / 24) * Math.PI * 2;
    const dist = 52 + (i % 3) * 8;
    const bh = TOWER_H * (0.55 + (i % 5) * 0.08);
    const bw = 12 + (i % 4) * 2;
    buildSurroundingTower(cityRoot, TOWER_CX + Math.cos(a) * dist, TOWER_CZ + Math.sin(a) * dist, bh, bw, 10 + (i % 3), i + 20);
  }

  const hill = new THREE.Mesh(new THREE.SphereGeometry(28, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2.1),
    mat(0x4a7850, { roughness: 0.95 }));
  hill.scale.set(2.2, 0.45, 1.8);
  hill.position.set(TOWER_CX - 58, 0, TOWER_CZ + 42);
  cityRoot.add(hill);

  [[-10, 6], [12, -5], [-8, -14], [10, 16]].forEach(([tx, tz], i) => {
    buildTree(cityRoot, TOWER_CX + tx, TOWER_CZ + tz, 0.85 + (i % 2) * 0.2);
  });
  [[-55, 55], [50, -50], [-58, -42]].forEach(([tx, tz], i) => {
    for (let j = 0; j < 4; j++) {
      buildTree(cityRoot, TOWER_CX + tx + j * 4, TOWER_CZ + tz + (j % 2) * 5, 1.1);
    }
  });

  [[TOWER_CX + 10, TOWER_CZ + 6], [TOWER_CX - 8, TOWER_CZ - 5], [TOWER_CX + 12, TOWER_CZ - 8]].forEach(([x, z], i) => {
    buildStreetLamp(cityRoot, x, z);
  });
  [[TOWER_CX + 11, TOWER_CZ + 2, 0.3], [TOWER_CX + 11, TOWER_CZ - 3, -0.2], [TOWER_CX - 9, TOWER_CZ + 4, 0.8]].forEach(([x, z, r]) => {
    buildParkedCar(cityRoot, x, z, r);
  });

  const podiumTex = canvasTex((g, w, h) => {
    g.fillStyle = "#949088";
    g.fillRect(0, 0, w, h);
    for (let x = 0; x < w; x += 28) {
      g.strokeStyle = "#848078";
      g.strokeRect(x + 1, 1, 24, h - 2);
    }
  }, 128, 64);
  podiumTex.repeat.set(3, 1);
  box(cityRoot, BE - BW + 3.2, 2.4, CL + 3.2, TOWER_CX, 1.2, TOWER_CZ,
    mat(0xffffff, { map: podiumTex, roughness: 0.72, metalness: 0.06 }), "Podium");
  box(cityRoot, BE - BW + 2.8, 0.12, CL + 2.8, TOWER_CX, 2.42, TOWER_CZ, mat(0xa8a4a0, { roughness: 0.68 }), "Podium-Cap");
  box(cityRoot, BE - BW + 3.6, 0.08, CL + 3.6, TOWER_CX, 0.04, TOWER_CZ, mat(0xc0bcb4, { roughness: 0.85 }), "Plaza-Ring");

  scene.add(cityRoot);
}

function buildFloorDetail(group, dy, model, failIds, clashZones) {
  const floorTile = canvasTex((g, w, h) => {
    g.fillStyle = "#ebe5db";
    g.fillRect(0, 0, w, h);
    g.strokeStyle = "rgba(180,170,155,0.35)";
    g.lineWidth = 1;
    for (let i = 0; i < w; i += 48) for (let j = 0; j < h; j += 48) g.strokeRect(i, j, 48, 48);
  }, 256, 256);
  floorTile.repeat.set(3, 12);
  const mWall = mat(0xf7f5f1, { roughness: 0.88 });
  const mTile = mat(0xffffff, { roughness: 0.72, map: floorTile, envMap, envMapIntensity: 0.12 });
  const mBase = mat(0xe0dcd4, { roughness: 0.8 });

  box(group, BE - BW, 0.1, CL + 0.3, TOWER_CX, dy + 0.05, TOWER_CZ, mTile, "Floor");
  box(group, BE - BW, WH, WT, TOWER_CX, dy + WH / 2, TOWER_CZ + CL / 2 + WT / 2, mWall, "Wall-N");
  box(group, WT, WH, CL, BW + WT / 2, dy + WH / 2, TOWER_CZ, mWall, "Wall-W");
  box(group, WT, WH, CL, BE - WT / 2, dy + WH / 2, TOWER_CZ, mWall, "Wall-E");
  box(group, BE - BW, 0.08, CL + 0.2, TOWER_CX, dy + 0.22, TOWER_CZ, mBase, "Baseboard");
  box(group, CW - 0.06, 0.06, CL - 0.2, CW / 2, dy + WH + 0.03, TOWER_CZ, mat(0xfcfcfa, { roughness: 0.94 }), "Ceiling");

  buildSouthGallery(group, dy);

  [2.5, 5.5, 8.5, 14, 17, 19.5].forEach((z, i) => {
    buildUnitRoom(group, dy, z, i + 1);
  });

  buildLiftLobby(group, dy);
  for (const d of model.doors || []) {
    buildStairwell(group, dy, d, failIds.has(d.id));
  }

  for (let z = 3; z < CL; z += 4.5) {
    box(group, 0.42, 0.02, 1.4, CW / 2, dy + WH - 0.03, TOWER_CZ + z - CL / 2,
      mat(0xffffff, { emissive: 0xfff6ea, emissiveIntensity: 0.55, roughness: 0.35 }), "Light");
  }

  for (const z of model.egress_zones || []) {
    const [cx, cz] = aabbCenter(z.aabb);
    const [sx, sz] = aabbSize(z.aabb);
    const clash = clashZones.has(z.id);
    const worldZ = TOWER_CZ + cz - CL / 2;
    box(group, sx, 0.04, sz, cx, dy + 0.08, worldZ,
      mat(clash ? 0xff6655 : 0x44bb77, { transparent: true, opacity: clash ? 0.42 : 0.22 }), z.id);
    registerMarker(z.id, cx, dy + 0.35, worldZ, z.name, clash ? "warn" : "ok");
  }

  for (const f of model.furniture || []) {
    const [cx, cz] = aabbCenter(f.aabb);
    const [sx, sz] = aabbSize(f.aabb);
    const isFail = failIds.has(f.id);
    if (f.id.includes("STROLLER")) {
      buildStroller(group, cx, TOWER_CZ + cz - CL / 2, dy, isFail);
    } else {
      buildCartonStack(group, cx, TOWER_CZ + cz - CL / 2, dy, sx, sz, isFail);
    }
  }

  // Fire hose cabinet embedded into west corridor wall.
  const hoseZ = TOWER_CZ + 10.8 - CL / 2;
  box(group, 0.14, 0.75, 0.48, 0.02, dy + 0.42, hoseZ, mat(0xcc3333, { roughness: 0.55 }), "Hose-Cabinet");
  box(group, 0.04, 0.65, 0.4, 0.08, dy + 0.42, hoseZ, mat(0xaa2222, { roughness: 0.5 }), "Hose-Door");
  box(group, 0.02, 0.08, 0.25, 0.1, dy + 0.72, hoseZ, mat(0xffffff, { emissive: 0xff0000, emissiveIntensity: 0.3 }), "Hose-Label");

  const interiorLight = new THREE.PointLight(0xfff6ec, 0.55, 16);
  interiorLight.position.set(CW / 2, dy + WH - 0.5, TOWER_CZ);
  group.add(interiorLight);
  const liftLight = new THREE.PointLight(0xf0f4ff, 0.35, 10);
  liftLight.position.set(CW + 1.2, dy + WH - 0.4, TOWER_CZ + 11 - CL / 2);
  group.add(liftLight);
}

function buildTowerExterior(group) {
  const activeY = floorY(ACTIVE);
  const lowerH = activeY;
  const upperBase = floorY(ACTIVE + 1);
  const upperH = floorY(TOTAL_FLOORS) + WH - upperBase;

  if (lowerH > 0.5) buildSolidTowerSection(group, 0, lowerH, 1);
  if (upperH > 0.5) buildSolidTowerSection(group, upperBase, upperH, 3);

  buildSectionCutFrames(group, activeY, upperBase);

  const roofY = floorY(TOTAL_FLOORS) + WH;
  box(group, BE - BW + 0.6, 0.35, CL + 0.6, TOWER_CX, roofY + 0.18, TOWER_CZ,
    mat(0x788898, { roughness: 0.5, metalness: 0.2, envMap, envMapIntensity: 0.3 }), "Roof");
  [[-1.2, -0.8], [1, 0.6], [-0.5, 1.1]].forEach(([rx, rz], i) => {
    box(group, 0.5, 0.4, 0.5, TOWER_CX + rx, roofY + 0.45, TOWER_CZ + rz, mat(0x606870, { roughness: 0.55 }), `AC-${i}`);
  });
}

function disposeObject(o) {
  if (o.geometry) o.geometry.dispose();
  if (o.material) {
    if (Array.isArray(o.material)) o.material.forEach((m) => m.dispose());
    else o.material.dispose();
  }
}

function buildFloorNav() {
  if (!floorNavEl) return;
  const floors = [];
  for (let f = TOTAL_FLOORS; f >= FLOOR_START; f -= 1) {
    if (f < ACTIVE - 4 || f > ACTIVE + 4) {
      if (f !== TOTAL_FLOORS && f !== FLOOR_START && f !== ACTIVE) continue;
    }
    floors.push(f);
  }
  floorNavEl.innerHTML = floors
    .map((f) => `<button type="button" class="floor-btn${f === ACTIVE ? " active" : ""}" data-floor="${f}">${f}F</button>`)
    .join("");
  floorNavEl.querySelectorAll(".floor-btn").forEach((btn) => {
    btn.addEventListener("click", () => jumpToFloor(Number(btn.dataset.floor)));
  });
}

function jumpToFloor(floor) {
  floorNavEl?.querySelectorAll(".floor-btn").forEach((b) => {
    b.classList.toggle("active", Number(b.dataset.floor) === floor);
  });
  const y = towerCenterY(floor);
  const endTarget = floor === ACTIVE
    ? new THREE.Vector3(TOWER_CX, y + 0.2, TOWER_CZ + 2)
    : new THREE.Vector3(TOWER_CX, y, TOWER_CZ);
  const endPos = floor === ACTIVE
    ? new THREE.Vector3(TOWER_CX + 5, y + 2.4, TOWER_CZ - CL / 2 - 7)
    : new THREE.Vector3(TOWER_CX + 28, y + 18, TOWER_CZ + 38);
  setOrbitLimits(floor === ACTIVE ? "floor" : "overview");
  flyAnim = {
    t0: performance.now(),
    duration: floor === ACTIVE ? 1000 : 850,
    startPos: camera.position.clone(),
    endPos,
    startTarget: controls.target.clone(),
    endTarget,
  };
  focusedId = floor === ACTIVE ? "FLOOR-23" : null;
  floorBadgeEl.textContent =
    floor === ACTIVE
      ? "23/F inspection floor · corridor egress compliance check"
      : `${floor}/F · wheel zoom · drag rotate (unlimited)`;
}

function buildSceneFromModel(model, result) {
  if (buildingRoot) {
    scene.remove(buildingRoot);
    buildingRoot.traverse(disposeObject);
  }
  markerMap = new Map();
  labelDefs = [];
  pulseMeshes = [];

  buildSky();
  if (!envMap) setupEnvMap();
  buildCityContext();
  buildFloorNav();

  buildingRoot = new THREE.Group();
  buildingRoot.name = "Building";

  const failIds = new Set(
    (result?.findings || []).filter((f) => f.severity === "fail").map((f) => f.element_id)
  );
  const clashZones = new Set(
    (result?.findings || [])
      .filter((f) => f.rule_id === "R2_EGRESS_ZONE_CLASH" && f.severity === "fail")
      .map((f) => f.measured?.egress_zone_id)
      .filter(Boolean)
  );

  buildTowerExterior(buildingRoot);

  const activeY = floorY(ACTIVE);
  buildFloorDetail(buildingRoot, activeY, model, failIds, clashZones);
  registerMarker("FLOOR-23", TOWER_CX, activeY + WH + 0.6, TOWER_CZ, "23/F inspection floor", "ok");

  scene.add(buildingRoot);
  updateLabels();
  setOverviewCamera(false);
}

function setOverviewCamera(animateFly = true) {
  const midY = floorY(TOTAL_FLOORS) * 0.48 + WH * 0.3;
  const endTarget = new THREE.Vector3(TOWER_CX, midY, TOWER_CZ);
  const endPos = new THREE.Vector3(TOWER_CX + 52, midY + 36, TOWER_CZ + 68);
  setOrbitLimits("overview");
  if (animateFly) {
    flyAnim = { t0: performance.now(), duration: 1200, startPos: camera.position.clone(), endPos, startTarget: controls.target.clone(), endTarget };
  } else {
    camera.position.copy(endPos);
    controls.target.copy(endTarget);
    controls.update();
  }
  focusedId = null;
  floorBadgeEl.textContent = "23/F inspection floor · full tower in ground-level city context";
}

function corridorFocusView(target) {
  const floorBase = floorY(ACTIVE);
  const eyeY = floorBase + 1.55;
  const lookY = floorBase + 1.2;
  const endTarget = new THREE.Vector3(target.x, lookY, target.z);
  const southBack = TOWER_CZ - CL / 2 + 1.8;
  const lookDist = Math.max(2.8, target.z - southBack);
  const endPos = new THREE.Vector3(
    THREE.MathUtils.clamp(target.x - 1.6, BW + 0.5, CW + 0.2),
    eyeY,
    THREE.MathUtils.clamp(target.z - Math.min(lookDist, 5.5), southBack, target.z - 1.0)
  );
  return { endPos, endTarget };
}

function focusCamera(id, duration = 900) {
  const pos = markerMap.get(id);
  if (!pos) return;
  let endPos;
  let endTarget;
  if (id === "FLOOR-23") {
    endTarget = pos.clone();
    endPos = pos.clone().add(new THREE.Vector3(12, 8, 18));
    setOrbitLimits("floor");
  } else {
    ({ endPos, endTarget } = corridorFocusView(pos));
    setOrbitLimits("detail");
  }
  flyAnim = {
    t0: performance.now(),
    duration,
    startPos: camera.position.clone(),
    endPos,
    startTarget: controls.target.clone(),
    endTarget,
  };
  focusedId = id;
  floorBadgeEl.textContent = id === "FLOOR-23"
    ? "23/F inspection floor · corridor egress compliance check"
    : `Focused on ${id} · free rotate/zoom/pan`;
  findingsEl.querySelectorAll("li[data-focus]").forEach((li) => {
    li.classList.toggle("focused", li.dataset.focus === id);
  });
}

function focusFloor23() {
  jumpToFloor(ACTIVE);
}

function updateLabels() {
  labelsEl.innerHTML = labelDefs
    .map((d) => `<div class="label-tag ${d.kind}" data-label-id="${d.id}" hidden>${d.label}</div>`)
    .join("");
}

function projectLabels() {
  const rect = canvasEl.getBoundingClientRect();
  for (const def of labelDefs) {
    const el = labelsEl.querySelector(`[data-label-id="${def.id}"]`);
    const world = markerMap.get(def.id);
    if (!el || !world) continue;
    const dist = camera.position.distanceTo(world);
    const show = def.id === "FLOOR-23" || def.id === focusedId || dist < 28;
    const p = world.clone().project(camera);
    if (p.z > 1 || !show) { el.hidden = true; continue; }
    el.hidden = false;
    el.style.left = `${((p.x + 1) / 2) * rect.width}px`;
    el.style.top = `${((1 - p.y) / 2) * rect.height}px`;
  }
}

function resize() {
  const rect = canvasEl.parentElement.getBoundingClientRect();
  const w = rect.width;
  const h = Math.max(rect.height, 520);
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  if (composer) {
    composer.setSize(w, h);
    const fxaaPass = composer.passes.find((p) => p.material?.uniforms?.resolution);
    if (fxaaPass) fxaaPass.material.uniforms.resolution.value.set(1 / w, 1 / h);
  }
}

window.addEventListener("resize", resize);
resize();

function animate(now) {
  requestAnimationFrame(animate);
  animClock += 0.04;
  const pulse = 0.55 + Math.sin(animClock) * 0.25;
  for (const m of pulseMeshes) {
    if (m.material?.emissive) m.material.emissiveIntensity = 0.28 + pulse * 0.22;
  }
  if (flyAnim) {
    const t = Math.min(1, (now - flyAnim.t0) / flyAnim.duration);
    const ease = 1 - Math.pow(1 - t, 3);
    camera.position.lerpVectors(flyAnim.startPos, flyAnim.endPos, ease);
    controls.target.lerpVectors(flyAnim.startTarget, flyAnim.endTarget, ease);
    if (t >= 1) flyAnim = null;
  }
  controls.update();
  projectLabels();
  if (composer) composer.render();
  else renderer.render(scene, camera);
}
requestAnimationFrame(animate);

function findingFocusId(f) {
  if (f.element_id && markerMap.has(f.element_id)) return f.element_id;
  if (f.measured?.door_id && markerMap.has(f.measured.door_id)) return f.measured.door_id;
  return f.element_id;
}

function renderExplainMode(explanation) {
  if (!explainModeEl) return;
  const mode = explanation?.mode || "unknown";
  explainModeEl.className = "explain-mode";
  if (mode === "llm_agent") {
    explainModeEl.classList.add("mode-llm");
    const modelTag = explanation?.llm_model ? ` (${explanation.llm_model})` : "";
    explainModeEl.textContent = `Explanation mode: llm${modelTag}`;
    explainModeEl.title = "LLM-generated explanation from deterministic findings.";
    return;
  }
  if (mode === "deterministic_agent_fallback") {
    explainModeEl.classList.add("mode-fallback");
    explainModeEl.textContent = "Explanation mode: deterministic fallback";
    explainModeEl.title = explanation?.fallback_reason || "LLM unavailable; using deterministic explanation.";
    return;
  }
  if (mode === "deterministic_agent") {
    explainModeEl.textContent = "Explanation mode: deterministic";
    explainModeEl.title = "Template-based deterministic explanation.";
    return;
  }
  explainModeEl.classList.add("muted");
  explainModeEl.textContent = `Explanation mode: ${mode}`;
  explainModeEl.title = "";
}

function renderResult(result) {
  const { summary, findings, explanation, model } = result;
  renderExplainMode(explanation);
  summaryEl.className = "summary";
  summaryEl.innerHTML = `
    <div class="stat fail"><b>${summary.fail}</b>fail</div>
    <div class="stat warn"><b>${summary.warn}</b>warn</div>
    <div class="stat pass"><b>${summary.pass}</b>pass</div>
  `;
  narrativeEl.textContent = explanation?.narrative || "";
  if (result.meta?.rules && ruleDescEl) {
    const cfg = result.meta.rule_config || {};
    ruleDescEl.textContent = `${result.meta.rules.map((r) => r.description).join(" · ")}. ${cfg.jurisdiction_note || ""}`.trim();
  }
  if (model) buildSceneFromModel(model, result);

  const important = findings.filter((f) => f.severity !== "pass");
  findingsEl.innerHTML = important
    .concat(findings.filter((f) => f.severity === "pass").slice(0, 2))
    .map((f) => {
      const focusId = findingFocusId(f);
      const canFocus = focusId && markerMap.has(focusId);
      return `<li class="${canFocus ? "clickable" : ""}" ${canFocus ? `data-focus="${focusId}"` : ""}><span class="badge ${f.severity}">${f.severity}</span><strong>${f.element_id}</strong> — ${f.message}${canFocus ? " ↗" : ""}</li>`;
    })
    .join("");

  findingsEl.querySelectorAll("li[data-focus]").forEach((li) => {
    li.addEventListener("click", () => focusCamera(li.dataset.focus));
  });

  actionsEl.innerHTML =
    (explanation?.recommended_actions || []).map((a) => `<li>${a}</li>`).join("") ||
    "<li>No actions needed.</li>";
}

async function runCheck(file) {
  if (explainModeEl) {
    explainModeEl.className = "explain-mode muted";
    explainModeEl.textContent = "Explanation mode: checking…";
    explainModeEl.title = "";
  }
  summaryEl.className = "summary muted";
  summaryEl.textContent = "Checking…";
  const res = file
    ? await fetch("/api/check", { method: "POST", body: (() => { const b = new FormData(); b.append("file", file); return b; })() })
    : await fetch("/api/check");
  if (!res.ok) throw new Error(await res.text());
  renderResult(await res.json());
}

btnSample.addEventListener("click", () => runCheck(null).catch((e) => { summaryEl.textContent = String(e); }));
btnFloor.addEventListener("click", focusFloor23);
btnOverview?.addEventListener("click", () => setOverviewCamera(true));
fileInput.addEventListener("change", () => {
  const f = fileInput.files?.[0];
  if (f) runCheck(f).catch((e) => { summaryEl.textContent = String(e); });
});

buildSky();
setupEnvMap();
setupPostProcessing();
buildCityContext();
buildFloorNav();
camera.position.set(TOWER_CX + 52, floorY(TOTAL_FLOORS) * 0.48 + 36, TOWER_CZ + 68);
controls.target.set(TOWER_CX, floorY(TOTAL_FLOORS) * 0.45, TOWER_CZ);
controls.update();
runCheck(null).catch((e) => { summaryEl.textContent = String(e); });
