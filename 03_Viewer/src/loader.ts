// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import * as FRAGS from "@thatopen/fragments";
import * as OBC from "@thatopen/components";
import type * as THREE from "three";
import type { ViewerConfig } from "./config";
import { getCachedFrag, putCachedFrag } from "./fragCache";

export interface LoaderContext {
  fragments: OBC.FragmentsManager;
  ifcImporter: FRAGS.IfcImporter;
  camera: THREE.PerspectiveCamera | THREE.OrthographicCamera;
}

export async function loadModelFromUrl(
  ctx: LoaderContext,
  url: string,
  name?: string,
): Promise<void> {
  const modelName =
    name ?? url.split("/").pop()?.replace(".ifc", "") ?? "model";

  console.log(`[PyNET Viewer] Loading: ${modelName} from ${url}`);

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }

  const buffer = await response.arrayBuffer();
  const bytes = new Uint8Array(buffer);

  // Cache key includes byte length so a re-exported file (different content) naturally
  // misses the cache instead of silently loading stale geometry.
  const cacheKey = `${url}|${bytes.byteLength}`;
  let fragBytes = await getCachedFrag(cacheKey);

  if (fragBytes) {
    console.log(`[PyNET Viewer] Cache hit: ${modelName} — skipping IFC parse`);
  } else {
    fragBytes = await ctx.ifcImporter.process({ bytes });
    await putCachedFrag(cacheKey, fragBytes);
  }

  await ctx.fragments.core.load(fragBytes, { modelId: modelName, camera: ctx.camera });

  console.log(`[PyNET Viewer] Loaded: ${modelName}`);
}

export async function loadAllModels(
  config: ViewerConfig,
  ctx: LoaderContext,
  onProgress?: (loaded: number, total: number, name: string) => void,
): Promise<void> {
  const total = config.modelUrls.length;
  for (let i = 0; i < total; i++) {
    const url = config.modelUrls[i];
    const name = url.split("/").pop()?.replace(".ifc", "") ?? `model-${i}`;
    onProgress?.(i, total, name);
    await loadModelFromUrl(ctx, url, name);
  }
  onProgress?.(total, total, "done");
}
