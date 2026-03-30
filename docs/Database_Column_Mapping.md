---
title: Database Column Mapping Reference
id: database-column-mapping
date: 2026-03-25
type: Reference
tags: [database, columns, mapping, everything-search, google-sheet, gemini, asset-pipeline]
status: Active
---

# Database Column Mapping Reference

This document serves as the master reference for the Google Sheet database column structure and its mapping to various asset categories. It is designed to ensure consistency for both human understanding and automated processing by Gemini and for effective searching within Everything Search.

## 1. Google Sheet Column Index (A-S)

The Google Sheet uses a fixed 19-column structure (A-S) for all asset types. Each column has a specific purpose, though its semantic interpretation may vary slightly depending on the asset category.

| Col | Letter | Column Name | General Purpose |
| :-- | :----- | :---------- | :-------------- |
| A   | 0      | `Rating`    | Quality or preference score (e.g., 1-5 stars) |
| B   | 1      | `Tags`      | Comma-separated keywords for general search |
| C   | 2      | `Filename`  | Relative path to the asset file (e.g., `Furniture/HermanMiller/EamesChair.jpg`) |
| D   | 3      | `URL`       | **Crucial:** Defines the asset category and routing key |
| E   | 4      | `From`      | Source or origin of the asset (e.g., `3dsky`, `CGTrader`, `Internal`) |
| F   | 5      | `Mood`      | Emotional or aesthetic feel (e.g., `Modern`, `Classic`, `Industrial`) |
| G   | 6      | `Author`    | Creator or designer of the asset |
| H   | 7      | `Writer`    | Brand or manufacturer of the asset |
| I   | 8      | `Album`     | Collection or model name (e.g., `EamesLounge`, `LC4`) |
| J   | 9      | `Genre`     | Primary color or material family (e.g., `DarkGrey`, `Leather`) |
| K   | 10     | `People`    | Contextual usage or location (e.g., `LivingRoom`, `Outdoor`) |
| L   | 11     | `Company`   | Shape or form descriptor (e.g., `Round`, `Pendant`) |
| M   | 12     | `Period`    | Material or finish (e.g., `Leather`, `Chrome`, `Wood`) |
| N   | 13     | `Artist`    | Style or design movement (e.g., `MidCentury`, `Scandinavian`) |
| O   | 14     | `Title`     | Primary name or identifier of the asset |
| P   | 15     | `Comment`   | Rich, Gemini-generated description and additional keywords |
| Q   | 16     | `To`        | Concatenated search string for Everything Search (legacy/manual) |
| R   | 17     | `Manager`   | Mirror of the `URL` column (Asset Category) |
| S   | 18     | `Subject`   | Secondary name or descriptor |

## 2. URL Column to Asset Category Mapping

The `URL` column (Column D) is the primary routing key for categorizing assets. Its value determines the specific semantic mapping for other columns and the Google Drive folder structure. Any row with an unrecognised `URL` value is silently skipped by the enrichment pipeline.

| URL Value (PascalCase) | Asset Group       | Description                                       |
| :--------------------- | :---------------- | :------------------------------------------------ |
| `Furniture`            | Furniture         | Chairs, sofas, tables, beds, storage, etc.        |
| `Fixture`              | Fixture           | Lighting, plumbing, appliances, doors, windows    |
| `Vegetation`           | Vegetation        | Trees, plants, shrubs, flowers                    |
| `Material`             | Material          | Material/texture swatches and thumbnails          |
| `Texture`              | Material          | Alias for `Material`                              |
| `People`               | People            | Human cutouts, 3D models of people                |
| `Object`               | FurnitureLike     | Props, accessories, decorative objects            |
| `Objects`              | FurnitureLike     | Alias for `Object`                                |
| `Digital`              | FurnitureLike     | Digital art, screens, electronic devices          |
| `Sports`               | FurnitureLike     | Sports equipment, gym gear                        |
| `Apparel`              | FurnitureLike     | Clothing, fashion items                           |
| `Vehicle`              | FurnitureLike     | Cars, bikes, boats, other vehicles                |
| `Buildings`            | Buildings         | Architectural elements, building models           |
| `Layouts`              | Layouts           | Floor plan arrangements, room setups              |
| `Layout`               | Layouts           | Alias for `Layouts`                               |

## 3. Semantic Field to Column Mapping by Asset Group

This section details how semantic fields (e.g., Brand, Model, Material) are mapped to the generic Google Sheet columns (A-S) for each specific asset group. This mapping is crucial for Gemini's data extraction and for constructing effective search queries.

### 3.1 Furniture & Fixture

| Semantic Field    | Google Sheet Column | Example Values (PascalCase) |
| :---------------- | :------------------ | :-------------------------- |
| **Asset Category**| `URL`               | `Furniture`, `Fixture`      |
| **Brand**         | `Writer`            | `HermanMiller`, `Grohe`     |
| **Collection/Model**| `Album`             | `EamesLounge`, `LC4`        |
| **Location**      | `People`            | `LivingRoom`, `Outdoor`     |
| **Material**      | `Period`            | `Leather`, `Chrome`, `Wood` |
| **Style**         | `Artist`            | `Modern`, `Scandinavian`    |
| **Shape/Form**    | `Company`           | `Round`, `Pendant`          |
| **Color**         | `Genre`             | `DarkGrey`, `MatteBlack`    |
| **SKU/Model No.** | `Author`            | `EA670`, `FLOS265`          |
| **Keywords**      | `Tags`              | `Upholstered`, `Swivel`     |
| **Description**   | `Comment`           | *Full Gemini-generated text*|
| **Search String** | `To`                | *Concatenation of all fields* |

### 3.2 Vegetation

| Semantic Field    | Google Sheet Column | Example Values (PascalCase) |
| :---------------- | :------------------ | :-------------------------- |
| **Asset Category**| `URL`               | `Vegetation`                |
| **Plant Type**    | `Mood`              | `Tree`, `Bush`, `Flower`    |
| **Latin Name**    | `Writer`            | `FicusLyrata`               |
| **Common Name**   | `Album`             | `FiddleLeafFig`             |
| **Location**      | `People`            | `Indoor`, `Outdoor`         |
| **Season**        | `Period`            | `Spring`, `Evergreen`       |
| **Style**         | `Artist`            | `Tropical`, `Minimalist`    |
| **Color**         | `Genre`             | `Green`, `Red`              |
| **Form**          | `Company`           | `Tall`, `Bushy`             |
| **Height**        | `Author`            | `200cm`, `Small`            |

### 3.3 Material/Texture

| Semantic Field    | Google Sheet Column | Example Values (PascalCase) |
| :---------------- | :------------------ | :-------------------------- |
| **Asset Category**| `URL`               | `Material`, `Texture`       |
| **Material Name** | `Mood`              | `Concrete`, `Marble`        |
| **Material Category**| `Period`            | `Stone`, `Fabric`           |
| **Surface**       | `Artist`            | `Rough`, `Polished`         |
| **Color**         | `Genre`             | `Grey`, `White`             |
| **Pattern**       | `Company`           | `Herringbone`, `Seamless`   |

### 3.4 People

| Semantic Field    | Google Sheet Column | Example Values (PascalCase) |
| :---------------- | :------------------ | :-------------------------- |
| **Asset Category**| `URL`               | `People`                    |
| **Gender**        | `Author`            | `Male`, `Female`            |
| **Ethnicity**     | `Writer`            | `Asian`, `Caucasian`        |
| **Age Group**     | `Album`             | `Adult`, `Child`            |
| **Pose**          | `Artist`            | `Standing`, `Sitting`       |
| **Clothing**      | `Period`            | `Casual`, `Formal`          |
| **Color**         | `Genre`             | `Black`, `White`            |
| **Location**      | `People`            | `Urban`, `Office`           |

### 3.5 Buildings

| Semantic Field    | Google Sheet Column | Example Values (PascalCase) |
| :---------------- | :------------------ | :-------------------------- |
| **Asset Category**| `URL`               | `Buildings`                 |
| **Subcategory**   | `Mood`              | `Facade`, `Roof`            |
| **Material**      | `Period`            | `Glass`, `Steel`            |
| **Style**         | `Artist`            | `Modern`, `Gothic`          |
| **Form**          | `Company`           | `Skyscraper`, `Dome`        |
| *(Color is intentionally omitted for Buildings to avoid conflicts with diagram backgrounds)* |

### 3.6 Layouts

| Semantic Field    | Google Sheet Column | Example Values (PascalCase) |
| :---------------- | :------------------ | :-------------------------- |
| **Asset Category**| `URL`               | `Layouts`                   |
| **Layout Type**   | `Mood`              | `FloorPlan`, `Section`      |
| **Room Type**     | `People`            | `LivingRoom`, `Bedroom`     |
| **Approx. Size**  | `Writer`            | `Small`, `Large`            |
| **Shape**         | `Period`            | `Rectangular`, `LShaped`    |

## 4. Key Design Rules & Conventions

-   **PascalCase for Values:** All database values (Brand, Material, Color, etc.) must use `PascalCase` with no spaces (e.g., `HermanMiller`, `DarkGrey`). Rules for conversion: remove all spaces, replace `&` with `And`, remove punctuation, capitalize each word.
-   **`From` Column (ID Generation):** The `From` column is used to generate a unique ID for each asset. It typically stores the source (e.g., `3dsky`, `CGTrader`) or an internal identifier.
-   **`To` Column (Everything Search):** This column is a concatenated string of all relevant metadata fields, designed for keyword searching in Everything Search. It is primarily for manual use and is generated by the `process_folder.py` script.
-   **`Tags` Column:** Contains comma-separated keywords. Duplicates are automatically removed during processing.
-   **`Comment` Column:** This is the rich, Gemini-generated description of the asset, containing a comprehensive set of keywords and contextual information.
-   **Google Drive Folder Structure:** Google Drive folders mirror the `URL` column values (e.g., `Furniture/`, `Fixture/`). Sub-folders within these categories also use `PascalCase` (e.g., `Furniture/HermanMiller/`).

## References

[1]: Naming_Convention.md
[2]: 3D_Asset_Workflow_Architecture.md
