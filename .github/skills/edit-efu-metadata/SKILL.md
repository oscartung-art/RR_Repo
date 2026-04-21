---
name: edit-efu-metadata
description: Updates any field in a .metadata.efu file for specific asset files. Use this skill when the user asks to rate assets, change subject, set title, update color, or modify any metadata field. The .metadata.efu is always co-located with the thumbnail files.
allowed-tools: shell, powershell
---

## edit-efu-metadata

Use this skill to update **any field** in the `.metadata.efu` file co-located with the asset files.

### Field reference

Parse the user's prompt to identify which field to change and map it to the EFU column name:

| User says           | `--field` to pass      | EFU column          |
|---------------------|------------------------|---------------------|
| rating, rate        | `Rating`               | Rating (1/25/50/75/99) |
| subject, category   | `Subject`              | Subject             |
| title, model name   | `Title`                | Title               |
| company, brand      | `Company`              | Company             |
| author, vendor      | `Author`               | Author              |
| album, collection   | `Album`                | Album               |
| tags                | `Tags`                 | Tags                |
| comment, notes      | `Comment`              | Comment             |
| period, style, era  | `Period`               | Period              |
| color, colour       | `color`                | custom_property_0   |
| location            | `location`             | custom_property_1   |
| form, shape         | `form`                 | custom_property_2   |
| chinese name        | `chinesename`          | custom_property_3   |
| latin name          | `latinname`            | custom_property_4   |
| size, dimensions    | `size`                 | custom_property_5   |

### Rating values

| Value | Meaning |
|-------|---------|
| `1`   | 1 ★     |
| `25`  | 2 ★★    |
| `50`  | 3 ★★★   |
| `75`  | 4 ★★★★  |
| `99`  | 5 ★★★★★ |

### Instructions

When the user asks to change metadata for asset files:

1. Identify the **field** from the prompt using the table above.
2. Extract the **value** to set.
3. Extract all **file paths** from the prompt (full Windows paths).
4. Run the script from tools/:

```
python "tools/edit_efu_metadata.py" --field <FIELD> --value "<VALUE>" "<FILE1>" "<FILE2>" ...
```

### Examples

**Rate files:**
> "rate these assets 99  
> G:\DB\mpm\mpmv04\RecessedSpotlights_94F58A3C.jpg  
> G:\DB\mpm\mpmv04\RecessedSpotlights_94F58A3C_01.jpg"

```
python "tools/edit_efu_metadata.py" --field Rating --value 99 "G:\DB\mpm\mpmv04\RecessedSpotlights_94F58A3C.jpg" "G:\DB\mpm\mpmv04\RecessedSpotlights_94F58A3C_01.jpg"
```

**Change subject:**
> "set subject to Fixture/Lighting/RecessedSpotLight for G:\DB\mpm\mpmv04\RecessedSpotlights_94F58A3C.jpg"

```
python "tools/edit_efu_metadata.py" --field Subject --value "Fixture/Lighting/RecessedSpotLight" "G:\DB\mpm\mpmv04\RecessedSpotlights_94F58A3C.jpg"
```

**Change title:**
> "change title to Onoк for G:\DB\mpm\mpmv04\RecessedSpotlights_94F58A3C.jpg"

```
python "tools/edit_efu_metadata.py" --field Title --value "Onok" "G:\DB\mpm\mpmv04\RecessedSpotlights_94F58A3C.jpg"
```

### How the script works

- The `.metadata.efu` is **always** in the same directory as the asset files.
- Files from different directories are grouped and each group's EFU is updated separately.
- Matching is done by **basename** so both full-path and basename EFU formats work.
- If a column doesn't exist in the EFU yet, it is appended.

### Optional flags

- `--dry-run` — Preview changes without writing (use when user says "preview" or "check").

### After running

Report to the user:
- Which field was changed and to what value
- How many files were updated
- Any files not found in the EFU
