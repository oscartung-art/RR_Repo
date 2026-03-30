---
title: Visualization Strategy: Birdseye
date: 2026-03-27
type: SOP
tags: [visualization, birdseye, environment, level-of-detail]
status: Active
---

# Visualization Strategy: Birdseye

This document outlines the level-of-detail (LOD) and composition strategy for birdseye (aerial) visualizations, ensuring high impact in hero areas while maintaining performance across large-scale environments.

## 1. Hero Buildings & Foreground
*   **Focus:** Main project buildings and immediate context.
*   **Interiors:** Populated with furniture and lighting.
*   **Vegetation:** High-density scattering using **Forest Pack + Splines** at each level/floor.
*   **Populating Assets:** Use proxy-merged furniture and high-quality people models.
*   **Density Metric:** Minimum of **120 people types** (6x22 distribution recommended).

## 2. Close Environment
*   **Focus:** Immediate surroundings and secondary context buildings.
*   **Asset Type:** Detailed building geometry.
*   **Workflow:** Utilize **RailClone** building generators for structural detail and variety.

## 3. Mid Environment
*   **Focus:** Wider context and urban fabric.
*   **Asset Type:** Representative building shapes.
*   **Detail:** Standard geometry with high-quality photo textures for realism.

## 4. Background Environment
*   **Focus:** Distant context, terrain, and horizon line.
*   **Terrain:** Base mesh with appropriate mapping.
*   **Trees:** Distant scatter-based vegetation.
*   **Buildings:** Low-poly box shapes with photo textures.
*   **Detail Constraints:**
    *   Minimum of **10 distinct photo textures**.
    *   Texture colors must be harmonious and unified with the project palette.
*   **Infrastructure:** Focus on **Road Centerlines** and basic road geometry.

## 5. Scene Composition (Asset List)
Use the following standardized assets/layers for consistent scene composition:

*   **Buildings:** `iB1000_Buildings`, `iB1000_FlatSurface_WithMapping`
*   **Masking:** `iB1000_TreeMask`
*   **Roads:**
    *   `Road_Close_SplineMesh`
    *   `Road_Side_Spline`: (CV Car/People Animation, RC Fence, RC Light Pole, FP People Stationary, RC Road Marking)
    *   `Road_CenterLine_Spline`: (Core traffic spline)
    *   `Road_Additional_Spline`: (Secondary traffic)
