---
title: 3ds Max Workflow SOP
date: 2026-03-27
type: SOP
tags: [3dsmax, workflow, performance, railclone, forestpack, civilview]
status: Active
---

# 3ds Max Workflow SOP

This document outlines standard operating procedures for 3ds Max to ensure optimal performance, scene organization, and cross-platform compatibility.

## 1. Performance & Viewport Optimization
*   **Subdivide N-gons:** Always subdivide N-gons for faster viewport performance.
*   **Avoid N-gon References:** Do not use N-gons for reference objects, as they cause significant lag and viewport instability.

## 2. Import & Export Best Practices
*   **Post-Import Routine:** Immediately after importing any external asset (CAD, FBX, OBJ):
    1.  **Attach:** Consolidate geometry where appropriate to reduce draw calls.
    2.  **Layering:** Move objects to relevant project layers immediately (see `Naming_Convention.md` for layer standards).
*   **Unreal Engine Export:**
    1.  **Spline Validation:** Ensure no overlapping splines exist; overlapping splines can cause Unreal Engine to hang during import/processing.
    2.  **RailClone Export:** Disable instancing and convert to **Proxy Mesh** before exporting to Unreal.

## 3. Plugin-Specific Workflows

### 3.1 RailClone (RC)
*   **Data Handling:** User data on markers cannot be used for **Generator** values; it is only compatible with **Node** values.
*   **Library Maintenance:** Use `Ctrl + S` to save library data **before** making any new modifications to prevent data loss.
*   **Alignment:** Set Z alignment to **Pivot** to ensure correct behavior, especially when working on building generators.
*   **Corners:** Unify building generator corners to **Bezier Corners** for consistent geometry generation.
*   **Sequencer Mode:** **Adaptive Mode** is unavailable when used with **Sequencer Mode** (geometry will be sliced).

### 3.2 Forest Pack (FP)
*   **Scene Layering:** Use FP for high-density scattering of vegetation and people (see `Visualization_Strategy_Birdseye.md`).

### 3.3 CivilView (CV)
*   **Units & Stations:** When working in **Centimeters (cm)**, do not use "Random Station." Always use **Fixed Station** for predictable placement along splines.

## 4. Scene Layering & Composition (Infrastructure)
Use these prefixes/layers for organizing infrastructure-heavy scenes:

*   **iB1000:** Prefix for "Infrastructure Base" or "Integrated Building" elements (e.g., `iB1000_Buildings`, `iB1000_TreeMask`).
*   **Road Hierarchy:**
    *   `Road_Close_SplineMesh`: High-detail road geometry.
    *   `Road_Side_Spline`: Spline for roadside assets (Fences, Lights).
    *   `Road_CenterLine_Spline`: Core spline for traffic and marking generation.
