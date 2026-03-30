---
title: Rhino to 3ds Max Export Workflow
date: 2026-03-27
type: SOP
tags: [rhino, 3dsmax, export, workflow, geometry]
status: Active
---

# Rhino to 3ds Max Export Workflow

This standard operating procedure ensures clean geometry transfer from Rhinoceros 3D into 3ds Max, preventing smoothing group errors and disorganized object hierarchies.

## 1. Export Settings in Rhino
When preparing your model in Rhino for export:
*   **Format:** Export the file as **Collada (`.dae`)**.
*   **Hierarchy:** Ensure you are exporting **from each layer** separately. This preserves your organizational structure when the geometry lands in 3ds Max.

## 2. Import & Cleanup in 3ds Max
Once the Collada file is imported into 3ds Max, perform the following cleanup steps on the geometry:
*   **Attach Objects:** Attach related objects together (e.g., combining loose surfaces into single logical meshes based on their material or layer).
*   **Auto Edge:** Apply an 'Auto Edge' (or adjust Smoothing Groups/Edit Normals) to fix the faceted or incorrect shading that often occurs when transferring NURBS-to-Mesh data.
