# Project Metadata Schema

This document defines the strict YAML front-matter schema for all project files in `projects/`. This ensures consistency across the Studio Brain, allowing terminal tools (`rr p`, `rr dash`) and AI agents to parse data without errors.

---

## 1. Top-Level Keys (Required)

| Key | Description | Example |
| :--- | :--- | :--- |
| `code` | Unique project identifier (Uppercase). | `PLS` |
| `name` | The full descriptive name of the project. | `Ping Lan Street` |
| `client` | The primary legal entity/SPV for the project. | `New Merit Limited (WO Properties)` |
| `f_drive_path` | Absolute path to the project mass on NAS. | `F:/PLS` |
| `status` | Current stage: `Lead`, `Active`, or `Completed`. | `Completed` |
| `last_updated` | Date of last significant metadata change. | `2026-03-30` |

---

## 2. Nested Data Blocks

### 2.1 `site_info`
Geographic and physical details of the project site.
*   `lot`: Official lot number (e.g., `APIL 32`).
*   `address`: Full physical address.

### 2.2 `contacts` (Role-Based)
Every contact block must correspond to an entry in `db/Master_CRM.csv`.
*   `client`: The project lead from the client side.
    *   `name`, `organization`, `email`, `phone`, `address`.
    *   `spv`: (Optional) Project-specific sub-company name.
*   `cg`: Your studio contact (usually `Oscar Tung`).
    *   `name`, `organization`, `email`, `phone`, `address`.
*   `team`: External consultants (use simple keys for roles).
    *   `architect`, `interior_design`, `landscape`, `structure`, `advertising`.

### 2.3 `links` (Symmetrical Drives)
Naming must strictly mirror the keys used in the `contacts` block, appended with `_drive`.
*   `client_drive`: Client's shared folder/Sharepoint.
*   `cg_drive`: RealRendering's Synology/Project share.
*   `architect_drive`: Architect's shared folder.
*   `interior_drive`: Interior designer's shared folder.

### 2.4 `design_documents`
Tracks the receipt and confirmation status of critical incoming project files. Keys MUST follow the Symmetrical Rule, matching the roles defined in `contacts`.
*   Status values should be: `Pending`, `Received`, or `Confirmed`.
*   Format: `[provider_role]: { [document_type_snake_case]: "[Status]" }`
*   Example Keys: `general_building_plan`, `camera_angle`, `model_3d`, `material_schedule`, `working_drawings`.

### 2.5 `gis`
Technical spatial data for engine/3D alignment.
*   `transformation`: String containing AxisX, AxisY, AxisZ, and Rotation.
*   `longitude`, `latitude`, `ib1000`, `ib5000`.

---

## 3. The Symmetrical Rule
To maintain a "Zero-Lock-In" easy-to-read system, **Contacts** and **Links** must be symmetrical.

**Correct:**
```yaml
contacts:
  team:
    architect: "MLA"
links:
  architect_drive: "https://..."
```

**Incorrect:**
```yaml
contacts:
  team:
    architect: "MLA"
links:
  mla_share: "https://..." # Proper name used instead of role key
```

---

## 4. Default Values
If a field is unknown, use a single dash `"-"`. Do not leave keys empty or delete them, as this helps scripts maintain a consistent table layout.
