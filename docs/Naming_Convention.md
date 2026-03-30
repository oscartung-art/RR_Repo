---
title: Naming Convention
date: 2026-03-26
type: Reference
tags: [naming, convention, files, folders, github, database, google-drive, 3dsmax, unreal-engine]
status: Active
---

# Naming Convention

## 1. Core Principle

Two rules govern everything:
1.  **Context Determines Case:** Code artifacts use lowercase with separators. Database values and human-facing identifiers use PascalCase. Documentation files use Title_Case.
2.  **Always Singular:** Never use plural nouns for folders, categories, or tags (e.g., use `Mesh` instead of `Meshes`, `Material` instead of `Materials`). This prevents ambiguity and matching errors.

This prevents ambiguity across tools — Python, PowerShell, Everything Search, Google Drive, and GitHub all behave consistently.

---

## 2. Scripts and Documentation

### 3.1 Python Script Names
Python scripts use `snake_case` (all lowercase, underscores) following a **verb_noun** pattern.
*   **Good:** `enrich_gdrive.py`, `match_schedule.py`
*   **Avoid:** `ProcessFolder.py`, `myScript.py`

### 3.2 Knowledge and Markdown Files
Markdown files in `docs/` use `Title_Case_With_Underscores.md`.
*   **Good:** `Naming_Convention.md`, `Asset_Workflow_Architecture.md`
*   **Avoid:** `naming.md`, `notes.md`

---

## 4. Database & Sync Layer (Google Sheets & Drive)

### 4.1 Database Values (Google Sheet)
All values use **PascalCase with no spaces** for Everything Search compatibility.
*   **General:** `Armchair`, `DarkGrey`, `LivingRoom`, `NaturalWood`.
*   **Brands:** Normalise to single PascalCase word (e.g., `B&B Italia` -> `BBItalia`, `Herman Miller` -> `HermanMiller`).

> **Exception - Master CRM:** To align natively with Google Workspace, the `db/Master_CRM.csv` database strictly uses **Standard Title Case** (e.g., `Jason Teo`, `Axxa Group`). This overrides the global PascalCase rule to prevent friction when syncing to phones and email clients.

### 4.2 Google Drive Folders
Folders use **PascalCase** to mirror the URL column values in the database (e.g., `Furniture/`, `Vegetation/`, `Material/`).

---

## 5. Studio Project Files (F:\ Drive)

Governs active project folders and files on the NAS.

### 5.1 Project Root Folders
*   **Format:** `[CODE]_[ProjectName]` (e.g., `3HG_HillGrove`).

### 5.2 Internal Folder Structure (The "Flat 3")
Every project is restricted to exactly three functional directories.
1.  `01_Brief/`: Incoming references, CAD, client PDFs, and feedback.
2.  `02_Work/`: Active production files (.skp, .max, .uproject).
3.  `03_Shared/`: Final renders, exported schedules, and client deliveries.

### 5.3 File Naming (General)
Underscores (`_`) are functional delimiters. Descriptions use PascalCase.
*   **01_Brief:** `YYYY-MM-DD_Description.ext`
*   **02_Work:** `CODE_Description_vXX.ext`
*   **03_Shared:** `YYYY-MM-DD_CODE_Description_vXX.ext`

### 5.4 Project-Specific Textures (Work-in-Progress Assets)
When a texture is extracted from a PDF or created specifically for a project, it is stored within that project's work folder until "promoted" to the global library.

*   **Location:** `F:\[CODE]_[ProjectName]\02_Work\Texture\`
*   **Naming Formula:** `T_[ProjectCode]_[Category]_[Description]_[Suffix].ext`
*   **Example:** `T_KIL112_Material_CustomWallpaperFloral_D.jpg`

**Library Promotion Workflow:** If an asset becomes useful for other projects, it is moved to `G:\`, the `[ProjectCode]` prefix is removed, and it is added to the global `_index.csv`.

---

## 6. 3ds Max & Unreal Workflow (RR-Standard)

### 6.1 Linear Versioning
To ensure consistency for both the artist and AI agents, use a **Linear Increment System**.
*   The highest version number is **always** the latest working file.
*   Never use words like "final", "latest", "new", or "old".
*   **3ds Max Formula:** `[ProjectCode]_[Location]_[Description]_v[###].max` (e.g., `MLS99_Podium_Master_v005.max`).

### 6.2 Object Naming (Unreal Export)
**Formula:** `[Prefix]_[Descriptor]_[###]`
*   **SM_**: **Static Mesh.** Unique, core geometry (Main structure).
*   **PH_**: **Placeholder.** Low-poly proxies for repeating assets (swapped in Unreal).
*   **LGT_**: **Light.** Positional helpers for lights.

### 6.3 Layer Naming
*   `01_EXPORT_STATIC`: Contains all `SM_` objects.
*   `02_EXPORT_PLACEHOLDERS`: Contains all `PH_` objects.
*   `03_EXPORT_HELPERS`: Contains `LGT_` positional placeholders.
*   `99_DO_NOT_EXPORT`: CAD plans, splines, old versions, helpers.

### 6.4 Material Naming (3ds Max & Unreal Sync)
Materials in 3ds Max must be named to match their intended **Unreal Engine Material Instance** to facilitate automatic assignment via Datasmith or FBX.

*   **Global Library:** `MI_[Category]_[Description]` (e.g., `MI_Wood_OakNatural`).
*   **Project-Specific:** `MI_[ProjectCode]_[Category]_[Description]` (e.g., `MI_3HG_Wallpaper_FloralCustom`).
*   **Texture Suffixes:**
    *   `_D`: Diffuse / Base Color
    *   `_N`: Normal
    *   `_R`: Roughness
    *   `_M`: Metallic
    *   `_O`: Ambient Occlusion
    *   `_E`: Emissive

---

## 7. Unreal Engine Content Structure (Flat & Prefix-Driven)

This structure minimizes folder depth, relying heavily on strict prefix naming and Unreal's built-in asset filters (and alphabetical sorting) to keep things organized without excessive clicking.

### 7.1 Directory Layout (Inside `Content/`)
*   `_Project/`: Project-specific logic, maps, and imports.
    *   `Map/`: Contains all `LV_` files.
    *   `Core/`: Flattened folder for project-specific Blueprints, Master Materials, and UI. Rely on `BP_`, `M_`, `WBP_` prefixes.
    *   `Mesh/`: Flattened folder for custom, project-specific meshes and their textures/materials.
    *   `Seq/`: Contains all `LS_` Level Sequences.
    *   `Datasmith/`: Contains raw Datasmith imports. Create a subfolder for each import (e.g., `Datasmith/Villa_v01/`). **Do not manually sort** the contents; let Datasmith keep its structure isolated here.
*   `Asset/`: Reusable library assets. Flattened by main category.
    *   `Furniture/`, `Vegetation/`, `Material/`: Inside these categories, files are completely flat. `SM_`, `MI_`, and `T_` files sit side-by-side. Use Unreal's Content Browser filters to isolate types.
*   `Plugin/`: Content from Marketplace plugins.

### 7.2 Asset Naming (Prefixes)
Assets must use standard UE prefixes followed by PascalCase descriptors.
**Formula:** `[Prefix]_[PascalCaseDescriptor]_[OptionalSuffix]`

*   `LV_`: Level / Map (e.g., `LV_13_18_28FTerrace`)
*   `SM_`: Static Mesh (e.g., `SM_KidsRoomLowCabinet`)
*   `SK_`: Skeletal Mesh (e.g., `SK_WalkingWoman`)
*   `M_`: Master Material (e.g., `M_BaseGlass`)
*   `MI_`: Material Instance (e.g., `MI_GlassFrosted`)
*   `T_`: Texture (e.g., `T_WoodOak_D`, where suffixes are `_D`, `_N`, `_R`, etc.)
*   `BP_`: Blueprint (e.g., `BP_LightFlicker`)

---

## 8. The "No-Break" Rules (ZIP Extraction & Safe Renaming)

When receiving packages (e.g., 3ds Max assets from 3dsky, or CAD Xref packages from architects), renaming internal files often breaks crucial software linkages.

**The Golden Rule:** Always extract the ZIP into a temporary staging folder, apply the Naming Convention to the **Parent Folder**, and leave the linked internal files alone.

| File Type | Can I Rename? | Rule |
| :--- | :--- | :--- |
| **Folder** | **YES** | **BEST PRACTICE:** Always rename the parent folder to match the convention. |
| **3ds Max (.max)** | **YES** | Usually safe to rename the file itself. |
| **Textures (.jpg/.png)** | **NO** | Never rename; it breaks the .max link resulting in missing assets. |
| **Host CAD (.dwg)** | **YES** | Safe to rename the "Master" file that receives the Xrefs. |
| **Xref CAD (.dwg)** | **NO** | Never rename; it breaks the host link. |

---

## 9. Global Library Asset Naming (G:\ Drive)
Assets promoted to the global library follow a brand-first or family-first convention to ensure perfect indexing in Everything Search.

**Formula:** `[Family]_[ModelName]_[Brand]`
*   **Family:** Matches the `Asset_Taxonomy_Reference.md` (e.g., `Armchair`, `Sofa`).
*   **Brand:** Normalized PascalCase brand name (e.g., `HermanMiller`).
*   **Example:** `Armchair_Eames_HermanMiller.zip`

---

## 10. Rendered Outputs & Deliverables (Ultra-Flat Overwrite Workflow)

This workflow prioritizes a flat folder structure and minimal file clutter by overwriting previous renders. 

### 9.1 The "ID-Anchor" Naming Formula
Use **Underscores (`_`)** to separate the Project and ID tokens, and **PascalCase** for the combined description.
**Formula:** `[ProjectCode]_[ID]_[Description].[ext]`

*   **Example:** `PLS_R07_GFLobbyGreen.png`
*   **ProjectCode:** Unique project identifier (e.g., `PLS`).
*   **ID:** The **Stable Anchor**. Increasing IDs (`R01`, `R02`...) that never change.
*   **Description:** A combined **PascalCase** string of the Subject and any Options (e.g., `GFLobbyGreen`).

### 9.2 The "Backstage vs. Showroom" Strategy
1.  **The Backstage (`02_Work/`):** Render all iterations here. Overwrite the file each time you render to keep the folder flat and current.
2.  **The Showroom (`03_Shared/`):** **Copy** only the specific "Committed" renders to this folder for the client.

### 9.3 Movie Render Queue (MRQ) Tokens (Unreal Engine)
To automate this, use the following string in the **Output > File Name Format** field:

`[ProjectCode]_{camera_name}`

*   **Camera Naming:** In the Unreal Outliner, name your cameras using the `[ID]_[Description]` format (e.g., `R07_GFLobbyGreen`).

`
---

## 10. Summary Reference Table

| Context | Convention | Example |
| :--- | :--- | :--- |
| GitHub Repo / Folder | `kebab-case` | `asset-pipeline`, `pipeline/` |
| Python Script | `snake_case` | `enrich_gdrive.py` |
| Knowledge File | `Title_Case` | `Naming_Convention.md` |
| DB / Drive Value | `PascalCase` | `HermanMiller`, `Furniture/` |
| Project Folder | `CODE_PascalCase` | `3HG_HillGrove` |
| 3ds Max File | `CODE_Loc_Desc_v###` | `MLS99_Podium_Master_v005.max` |
| 3D Object (Mesh) | `SM_Desc_###` | `SM_Lobby_MainWall_001` |
| 3D Object (Proxy) | `PH_Desc_###` | `PH_Chair_Eames_042` |
| Material Instance | `MI_Desc` | `MI_Wood_Walnut` |
| Texture Map | `T_Desc_Suffix` | `T_Wood_Walnut_D` |
| UE Level / Map | `L_PascalCase` | `L_13_18_28FTerrace` |
| UE Asset (Mesh/Mat/BP) | `Prefix_PascalCase` | `SM_KidsRoomCabinet` |
| Rendered Output | `CODE_Desc_v###` | `KIL112_MainView_v001.jpg` |

---

## 11. Action Log Status Tags

The `log/action_log.md` file uses a strict set of status tags. No other tags are permitted.

*   `Pending`: The task is in the queue but has not been started.
*   `In Progress`: The task is actively being worked on.
*   `Blocked`: The task is blocked by a dependency or an external factor.
*   `Done`: The task is complete.
*   `Cancelled`: The task is no longer relevant.

---

## 12. Asset & Scene Prefixes (Consolidated)

This section provides a master list of all approved prefixes for different asset types and scene organization layers across all workflows.

### 12.1 General Asset Prefixes
| Code | Type | Description |
| :--- | :--- | :--- |
| **BP** | Blueprint | Unreal Engine Blueprint asset. |
| **CAD**| CAD Drawing | Imported CAD files. |
| **CO** | Cutout | 2D cutout assets (e.g., people, trees). |
| **FP** | ForestPack | Forest Pack Pro object. |
| **HDR**| HDRI | High Dynamic Range Image for lighting. |
| **LGT**| Light | 3ds Max light object placeholder. |
| **LV** | Level / Map | Unreal Engine Level (Map) file. |
| **M**  | Master Material | Unreal Engine Master Material. |
| **MI** | Material Instance | Unreal Engine Material Instance. |
| **MS** | Megascans | Placeholder for Megascans assets (to be confirmed). |
| **PH** | Placeholder | Low-poly proxy object for Unreal export. |
| **RC** | RailClone | RailClone Pro object. |
| **SK** | Skeletal Mesh | Unreal Engine Skeletal Mesh. |
| **SM** | Static Mesh | Static Mesh geometry. |
| **TX** | Texture | General texture maps (use T_ prefix for UE). |

---

## 13. Data Integrity & Schema
For rules regarding the internal YAML structure of project files and how they link to the Master CRM, refer to [Project_Metadata_Schema.md](Project_Metadata_Schema.md).


### 12.2 3ds Max Infrastructure Prefixes
| Code | Type | Description |
| :--- | :--- | :--- |
| **iB1000** | Infrastructure | For "Infrastructure Base" or "Integrated Building" elements. |
| **Road_** | Road Hierarchy | Prefixes for organizing road splines (e.g., `Road_Close_`, `Road_Side_`). |

`
