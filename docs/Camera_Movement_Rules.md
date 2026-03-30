---
title: Camera Setup & Movement Guide
date: 2026-03-27
type: SOP
tags: [unreal-engine, camera, animation, rules]
status: Active
---

# Camera Setup & Movement Rules

This document defines the studio standards for setting up cameras and animating them, primarily for Unreal Engine 5. It ensures consistency across all architectural visualizations.

## 1. General Principles
*   **Average Animation Duration:** 3 minutes total.
*   **Image Proportion:** Panoramic formats are preferred to concentrate visual focus on the central part of the image.
*   **Performance:** Digital file formats, compression, and rendering capabilities must be planned early as they condition storage and processing time.

## 2. Types of Movement
Cameras are categorized into two types: those that physically move through space, and those that remain stationary but rotate/zoom.

### A. Camera WITH Movement
*   **Truck:** Moving the camera physically left or right.
*   **Dolly:** Moving the camera physically forward (Push) or backward (Pull).
*   **Pedestal:** Moving the camera physically up or down.
*   **Orbit:** Moving the camera in a circular path around a central subject.

### B. Camera NO Movement (Stationary)
*   **Pan:** Rotating the camera head horizontally (left/right).
*   **Tilt:** Rotating the camera head vertically (up/down).
*   **Zoom:** Changing the focal length (FOV).

## 3. Standard Velocities & Trajectories
To maintain realism and avoid motion sickness, adhere to these standard speeds:

*   **Rotations (Pan/Tilt):** Average angular velocity of **8 degrees per second**.
    *   *Extension:* Around 42 degrees total (less than a full image). Usually used to relate two facades/sides of a room.
*   **Pedestrian Walk (Dolly/Truck):** Regular speed of **1.2 meters per second**.
*   **Aerial Views (Dolly/Truck):** Ranges from **7 to 15 meters per second**.
    *   *Trajectories:* Keep trajectories reduced. About 1/6th of the building length for outdoors, or 1/3rd of the room length for indoors. Use ample curves and slanted visual directions.

## 4. Standard Camera Angles & Levels
Use these abbreviations when naming or logging shots.

### Angles
*   **WV:** Worm's Eye View (Highlights scale of construction)
*   **LV:** Low Angle
*   **NV:** Normal Angle
*   **HV:** High Angle
*   **BV:** Birdseye View

### Camera Levels
*   **Birdseye:** Top-down.
*   **Close up Aerial:** Highlights building features.
*   **Eye Level:** Most relational, connects the viewer to the space.
*   **Worm's Eye:** Looking up, highlights scale.
*   **Close Up:** Highlights specific details (materials, furniture).
*   **Aerial:** General wide view from above.
*   **Wide Angle:** Captures the whole room/facade.

## 5. Shot Naming & Logging Convention
When logging shots for a project (e.g., in a spreadsheet or GitHub issue), use the following structure:
`Location_Angle_FOV_Motion_Lighting`

**Examples:**
*   `Pool_NE.Normal.Medium.Truck.Day`
*   `Functionroom1.BV.35.Orbit.Day`
*   `Functionroom1-S_NV_35_Dolly_Day`

## 6. Standard Shot List Matrix
Below is a reference matrix of standard shots, the preferred camera motion, and the focus of the shot.

| Scene | Location | Camera Motion | Focus / Notes |
| :--- | :--- | :--- | :--- |
| **Interior** | Dining Table | Dolly | - |
| **Exterior** | Hero (Overview) | Dolly (Push/Pull) / Truck | Relation Context, Sun/Dust Lighting |
| **Exterior** | Entrance (Roundabout) | Orbit | Water Animation |
| **Exterior** | Main Entrance | Dolly | Door Open, Tree Foreground |
| **Interior** | GF Lobby | Dolly | - |
| **Interior** | Lounge | Pedestal / Orbit | Reveal Pool / Dining Table / Counter |
| **Interior** | Lounge (Sofa) | Dolly / Truck | 45 Degree, Show Furniture Form |
| **Interior** | Function Room (Dining) | Dolly | - |
| **Interior** | Function Room (Pendant) | Orbit (DOF) | Water |
| **Interior** | Kids Room | Dolly | 30 Degree, Show Furniture Form |
| **Interior** | Gym | Dolly | Sun Position |
| **Exterior** | Gym Exterior | Orbit / Pedestal | - |
| **Exterior** | Landscape | Truck / Dolly / Pedestal | Highlight features |
| **Exterior** | Pool | Dolly / Truck | Highlight, Water, Tree Foreground |
| **Detail** | Pool | Truck (DOF) | Water Highlight, Facade to Lantern |
| **Exterior** | Facade | Truck / Pedestal | Sun, Tree |
| **Interior** | Lobby | Orbit | Residential Lobby, Furniture Form |
| **Interior** | Balcony | Dolly (Push) | Relation: Interior/Exterior |
| **Exterior** | Roof | Dolly (Push) | Water, Highlight, Relation: Int/Ext |
| **Exterior** | Landscape (Pavilion) | Dolly (Pull) | Pavilion Form |
| **Exterior** | BBQ | Orbit | Furniture (Sun Lighting) |
