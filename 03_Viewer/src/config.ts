// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

export interface ViewerConfig {
  modelUrls: string[];
  serverBase: string;
  autoLoad: boolean;
}

declare global {
  interface Window {
    VIEWER_CONFIG?: Partial<ViewerConfig>;
  }
}

export function getConfig(): ViewerConfig {
  const defaults: ViewerConfig = {
    modelUrls: [],
    serverBase: window.location.origin,
    autoLoad: true,
  };

  // Priority 1: window.VIEWER_CONFIG (set by parent page)
  if (window.VIEWER_CONFIG) {
    Object.assign(defaults, window.VIEWER_CONFIG);
  }

  // Priority 2: URL query parameters
  const params = new URLSearchParams(window.location.search);

  const modelsParam = params.get("models");
  if (modelsParam) {
    defaults.modelUrls = modelsParam.split(",").map((m) => {
      const trimmed = m.trim();
      if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
        return trimmed;
      }
      return `${defaults.serverBase}/models/${trimmed}`;
    });
  }

  const autoLoad = params.get("autoLoad");
  if (autoLoad !== null) {
    defaults.autoLoad = autoLoad !== "false";
  }

  return defaults;
}
