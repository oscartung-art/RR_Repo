---
title: GIS Data Integration SOP (HK Standard)
date: 2026-03-27
type: SOP
tags: [gis, ib1000, planning, shapefile, geojson, hk-standard]
status: Active
---

# GIS Data Integration SOP (HK Standard)

This document outlines the workflow for integrating official Hong Kong GIS data, specifically the **iB1000** Topographic Map and the **Digital Planning Data** from the Planning Department.

## 1. iB1000 (Intelligent B1000) Data
The `iB1000` prefix in 3ds Max scenes indicates geometry derived from the Hong Kong Lands Department 1:1000 Digital Topographic Map.

### Standard iB1000 Layers/Assets:
*   **`iB1000_Buildings`**: Extruded building footprints based on official records.
*   **`iB1000_FlatSurface`**: Ground surfaces, including roads and open spaces, usually with mapping coordinates.
*   **`iB1000_TreeMask`**: Data points or areas identifying official vegetation zones.

## 2. Digital Planning Data (Statutory Plans)
Derived from the Planning Department (TPB), this data defines the legal constraints of a site.

### Data Types:
1.  **Statutory Planning Scheme Boundary**: The overall extent of the planning area.
2.  **Zoning Boundaries**: Land use designations (e.g., Residential, Commercial, G/IC).
3.  **Building Height Control Areas**: Critical for validating building massing.
4.  **Amendment Items**: Recent changes to the statutory plan.

### Supported File Formats:
*   **Shapefile (.shp)**: Preferred for 3ds Max integration via CivilView or Link ADT.
*   **GML**: XML-based geographical data.
*   **GeoJSON**: Lightweight format, often used for web-based GIS or Unreal Engine integration.

## 3. Integration Workflow
1.  **Coordinate Consistency:** Always ensure the project uses the **HK1980 Grid System**. Do not move GIS data away from its origin; move the 3ds Max "User Grid" or use a Global Offset.
2.  **Attribute Preservation:** When importing Shapefiles, preserve object names and attributes (e.g., zoning codes) to ensure the scene remains searchable.
3.  **Visualization:**
    *   **Zoning:** Use standardized semi-transparent colors to represent different land use zones in 3ds Max.
    *   **Height Limits:** Create volumes (Boxes) based on the "Building Height Control Area" to verify design compliance.
