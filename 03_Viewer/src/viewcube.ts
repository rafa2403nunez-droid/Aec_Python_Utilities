// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import * as THREE from "three";
import * as OBC from "@thatopen/components";

function makeFaceTex(label: string, bg: string): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 128; c.height = 128;
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, 128, 128);
  ctx.strokeStyle = "rgba(255,255,255,0.14)";
  ctx.lineWidth = 4;
  ctx.strokeRect(3, 3, 122, 122);
  ctx.fillStyle = "#d0d4e8";
  ctx.font = "bold 24px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, 64, 64);
  return new THREE.CanvasTexture(c);
}

function makeSprite(text: string, color: string): THREE.Sprite {
  const c = document.createElement("canvas");
  c.width = 64; c.height = 64;
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = color;
  ctx.font = "bold 36px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 32, 32);
  const mat = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true });
  const sp = new THREE.Sprite(mat);
  sp.scale.set(0.26, 0.26, 1);
  return sp;
}

export function createViewCube(
  camera: OBC.OrthoPerspectiveCamera,
  container: HTMLElement,
  // Radians the model geometry is rotated about the vertical axis in world space (baked-in
  // true-north rotation). The cube's Front/Left/… must snap to the model's axes, not the
  // world's, so every face azimuth is offset by this. Read live so it can update after the
  // package metadata loads.
  getNorthOffset: () => number = () => 0,
): void {
  const PX = 120;

  const cvs = document.createElement("canvas");
  Object.assign(cvs.style, {
    position: "absolute",
    bottom: "7rem",
    right: "0.5rem",
    width:  `${PX}px`,
    height: `${PX}px`,
    cursor: "pointer",
    zIndex: "8",
  });
  container.appendChild(cvs);

  const rdr = new THREE.WebGLRenderer({ canvas: cvs, antialias: true, alpha: true });
  rdr.setPixelRatio(window.devicePixelRatio);
  rdr.setSize(PX, PX);
  rdr.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();

  // ── ViewCube camera — same front direction as the original working version ──
  const vcCam = new THREE.PerspectiveCamera(38, 1, 0.1, 10);
  vcCam.position.set(0, 0, 2.7);

  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  const dir = new THREE.DirectionalLight(0xffffff, 1.0);
  dir.position.set(1.5, 2, 2.5);
  scene.add(dir);

  // ── Cube ─────────────────────────────────────────────────────────────────────
  // BoxGeometry material order: +X RIGHT, -X LEFT, +Y TOP, -Y BOTTOM, +Z FRONT, -Z BACK
  const S = 0.74;
  const mats = [
    new THREE.MeshPhongMaterial({ map: makeFaceTex("RIGHT",  "#283548"), shininess: 50 }),
    new THREE.MeshPhongMaterial({ map: makeFaceTex("LEFT",   "#283548"), shininess: 50 }),
    new THREE.MeshPhongMaterial({ map: makeFaceTex("TOP",    "#1e3a28"), shininess: 50 }),
    new THREE.MeshPhongMaterial({ map: makeFaceTex("BOTTOM", "#2a1e3a"), shininess: 50 }),
    new THREE.MeshPhongMaterial({ map: makeFaceTex("FRONT",  "#1e2848"), shininess: 50 }),
    new THREE.MeshPhongMaterial({ map: makeFaceTex("BACK",   "#2a2040"), shininess: 50 }),
  ];
  const cube = new THREE.Mesh(new THREE.BoxGeometry(S, S, S), mats);
  scene.add(cube);

  cube.add(new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(S, S, S)),
    new THREE.LineBasicMaterial({ color: 0x7788bb, transparent: true, opacity: 0.55 }),
  ));

  // ── Compass group (azimuth only) ──────────────────────────────────────────────
  const compassGroup = new THREE.Group();
  const R = 0.66, CY = -(S / 2) - 0.14;
  for (const [t, x, z] of [["N",0,R],["S",0,-R],["E",R,0],["W",-R,0]] as [string,number,number][]) {
    const sp = makeSprite(t, "#8899bb");
    sp.position.set(x, CY, z);
    compassGroup.add(sp);
  }
  const ringGeo = new THREE.RingGeometry(0.50, 0.57, 64);
  ringGeo.rotateX(-Math.PI / 2);
  const ringMesh = new THREE.Mesh(ringGeo,
    new THREE.MeshBasicMaterial({ color: 0x4a5a88, side: THREE.DoubleSide, transparent: true, opacity: 0.55 }));
  ringMesh.position.y = CY;
  compassGroup.add(ringMesh);
  scene.add(compassGroup);

  // ── Click / hover ─────────────────────────────────────────────────────────────
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();

  const getHit = (e: MouseEvent) => {
    const rect = cvs.getBoundingClientRect();
    ptr.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1;
    ptr.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1;
    ray.setFromCamera(ptr, vcCam);
    const hits = ray.intersectObject(cube, false);
    return hits.length ? hits[0] : null;
  };

  const origColors = mats.map(m => m.color.clone());
  let hovered = -1;

  cvs.addEventListener("click", (e) => {
    const hit = getHit(e);
    if (!hit?.face) return;

    // face.normal is in BoxGeometry LOCAL space: always (±1,0,0), (0,±1,0) or (0,0,±1).
    // camera-controls spherical: x=sin(pol)*sin(az), y=cos(pol), z=sin(pol)*cos(az)
    // So acos(n.y) → polar, atan2(n.x, n.z) → azimuth maps each face correctly.
    const n = hit.face.normal;
    const polar   = Math.acos(Math.max(-1, Math.min(1, n.y)));
    const azimuth = Math.atan2(n.x, n.z);

    // Face azimuth is in the model (building) frame; convert to world by adding the north offset.
    camera.controls.rotateTo(azimuth + getNorthOffset(), polar, true);
  });

  cvs.addEventListener("mousemove", (e) => {
    const hit = getHit(e);
    const fi = hit ? Math.floor(hit.faceIndex! / 2) : -1;
    if (fi === hovered) return;
    if (hovered >= 0) mats[hovered].color.copy(origColors[hovered]);
    if (fi >= 0) mats[fi].color.setHex(0x7799dd);
    hovered = fi;
    cvs.style.cursor = fi >= 0 ? "pointer" : "default";
  });

  cvs.addEventListener("mouseleave", () => {
    if (hovered >= 0) { mats[hovered].color.copy(origColors[hovered]); hovered = -1; }
  });

  // ── Render loop ───────────────────────────────────────────────────────────────
  // The cube and compass track the camera, but expressed in the MODEL (building) frame —
  // i.e. the world rotated about the vertical by the north offset. This makes the cube's
  // FRONT/LEFT/… faces and the compass N align with the building, not the world axes.
  const _q     = new THREE.Quaternion();
  const _qAdj  = new THREE.Quaternion();
  const _northQ = new THREE.Quaternion();
  const _UP    = new THREE.Vector3(0, 1, 0);
  const _eu    = new THREE.Euler();

  const tick = () => {
    requestAnimationFrame(tick);
    camera.three.getWorldQuaternion(_q);
    _northQ.setFromAxisAngle(_UP, -getNorthOffset());
    _qAdj.copy(_northQ).multiply(_q);
    cube.quaternion.copy(_qAdj).invert();
    _eu.setFromQuaternion(_qAdj, "YXZ");
    compassGroup.quaternion.setFromEuler(new THREE.Euler(0, -_eu.y, 0));
    rdr.render(scene, vcCam);
  };
  tick();
}
