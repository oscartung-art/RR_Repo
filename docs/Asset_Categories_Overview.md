# 3D Asset Categories & Automation Workflow

This document provides a high-level overview of how your 3D assets are organized on `G:\3D` and the automated workflow that manages them.

## 1. Asset Organization Strategy
Your assets are primarily organized by **Source** or **Collection**, and then sub-categorized by **Type**.

### The 3dsky / BY CGI / HC Standard
These collections follow a standardized numbering system:
*   **01-沙发 (Sofa):** Single, 2-seater, Multi-seater, Daybeds.
*   **02-床沙发茶几 (Living Set):** Coffee tables, Side tables.
*   **03-椅凳 (Chair):** Armchairs, Dining chairs, Stools.
*   **04-桌子 (Desk):** Desks, Dining tables, Side tables.
*   **05-床具 (Bed):** Beds, Bedroom sets.
*   **06-柜架 (Cabinet):** Wardrobes, TV cabinets, Shelves.
*   **07-厨房 (Kitchen):** Kitchenware, Food, Drink, Cabinets.
*   **08-卫浴 (Bathroom):** Toilets, Basins, Faucets, Showers.
*   **09-材质 (Material):** Floors, Walls, Glass, Wood.
*   **10-灯具 (Lamps):** Ceiling, Wall, Table, Floor.
*   **11-电器 (Electrical):** TV, Computers, Gym equipment.
*   **12-陈设 (Set/Decor):** Curtains, Paintings, Books, Carpets.
*   **13-动植 (P&A):** Interior/Exterior plants, Animals.
*   **14-汽车交通 (Car):** Vehicles.
*   **15-人物 (Figure):** People models.

### Major Manufacturer & Boutique Collections
*   **Dedon / Kettal:** Specialized outdoor furniture organized by product line (e.g., *BABYLON*).
*   **m+m:** Volumetric collections (e.g., *Vol 01-Accessories*).
*   **Maxtree / Globe Plants:** High-end vegetation (V01-V83).
*   **Evermotion:** Classic Archmodels sets (AM154, AM210).
*   **Megascans:** Surfaces, 3D plants, and Atlases.

## 2. Asset Management Automation Workflow

This workflow automates the matching of designer schedules against your local database, avoiding proprietary lock-in.

### Data Layer Architecture
The database is built on open, user-editable formats:
*   **Asset Storage:** Google Drive (mirrored locally to `D:\`). Provides cloud backup with local speed.
*   **Master Database:** `_index.csv`. Open format, easily searchable.
*   **Enrichment Pipeline:** Python + Gemini API. Extracts structured metadata from images (`process_folder.py`).

### Daily Search Interface
*   **Export:** Data from the CSV index is exported to an EFU (Everything File List) file.
*   **Search Engine:** **Everything Search** indexes the EFU.
*   **Querying:** A custom filter (`to:<#param:`) directs searches to the `To` column (the concatenated search string). Searching "black eames chair" instantly filters the library.

### Automated Schedule Matching Pipeline
*   **`match_schedule.py`:** Reads schedules (PDF via Gemini API, or Excel). Extracts structured items (Code, Brand, Model, Item Name). Fuzzy matches against the CSV data using `RapidFuzz` in Python. Classifies matches (Found, Review, Not Found).
*   **`report.py`:** Outputs a clean Excel report containing the match status and local file path.
