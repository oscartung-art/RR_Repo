# Everything Search Metadata Columns

Reference for all available metadata columns in `.metadata.efu`. Defines column names, data types, and semantic mappings for core fields, categorization, descriptive attributes, and custom properties.

## Overview

The metadata system uses `custom_property_0` through `custom_property_9` for all asset-specific enrichment. The **semantic meaning of each custom property varies depending on the asset type**. The column headers remain the same, but how you interpret them changes for each asset category.

## Core Fields

| Column Name | Description |
|---|---|
| `Filename` | Asset filename (read-only, used for matching) |
| `Rating` | Star rating as numeric value (1, 25, 50, 75, 99) |
| `CRC-32` | Checksum of source archive file (read-only) |
| `Comment` | Free-text notes, warnings, status, or additional info |
| `Tags` | Semicolon-delimited keyword list |
| `Content Status` | Asset lifecycle status or review stage |

---

## Asset Type Custom Property Mappings

### Furniture & Fixture & Object

| Custom Property | Description | Enrichment Method |
|---|---|---|
| `custom_property_0` | Primary asset classification | AI determines leaf subject phrase, prefixed with asset category root (e.g., Furniture/Armchair) |
| `custom_property_1` | Model name or designer name | Extracted from filename or context (e.g., Barcelona, Eames Lounge) |
| `custom_property_2` | Brand/Designer/Collection identifier | Extracted from filename context or domain knowledge (e.g., BBItalia, Herman Miller) |
| `custom_property_3` | Style or era classification | AI vision analysis identifies design style (e.g., Modern, Contemporary, Mid-Century, Industrial) |
| `custom_property_4` | Primary color or material or surface finish | AI vision analysis extracts dominant color from image or OCR from schedule (e.g., Chrome, Matte Black, Wood) |
| `custom_property_5` | Usage context or location | AI reasoning determines appropriate usage context (e.g., Living Room, Bedroom, Office) |
| `custom_property_6` | Shape or physical configuration | AI vision analysis identifies geometric form (e.g., Round, Rectangular) |
| `custom_property_7` | Dimensions or scale classification | Extracted from metadata or AI scale estimation (e.g., 300x300mm, 1200x450x350mm) |
| `custom_property_8` | Reference code | OCR extracted from schedule specifications, filename (e.g., AL-01, GL-02, ST-03) |
| `custom_property_9` | Reserved | Unused |

### Vegetation

| Custom Property | Description | Enrichment Method |
|---|---|---|
| `custom_property_0` | Primary asset classification | AI determines leaf subject phrase, prefixed with asset category root (e.g., Vegetation/Tree, Vegetation/Shrub) |
| `custom_property_1` | Common Name of Vegetation | AI plant classification provides common name, learns from chinese and latin (e.g., Birds of Paradise, Fig Leaf) |
| `custom_property_2` | Plant Secondary Besides Green | AI vision analysis extracts dominant color from image (e.g., Pink, Yellow, Red) |
| `custom_property_3` | Plant Shape | AI vision analysis identifies geometric form/growth pattern (e.g., Columnar, Spreading) |
| `custom_property_4` | Chinese scientific name | AI plant classification provides scientific name (e.g., 栎树, 月季, 仙人掌) |
| `custom_property_5` | Latin scientific name | AI plant classification provides scientific name (e.g., Quercus robur, Rosa damascena) |
| `custom_property_6` | Plant Height, Spread, Radius..etc | Extracted from metadata or AI scale estimation (e.g., 3m, 5m) |
| `custom_property_7` | Reserved | Unused |
| `custom_property_8` | Reference code | OCR extracted from schedule specifications, filename (e.g., AL-01, GL-02) |
| `custom_property_9` | Reserved | Unused |

### Material

| Custom Property | Description | Enrichment Method |
|---|---|---|
| `custom_property_0` | Primary asset classification | AI determines leaf subject phrase, prefixed with asset category root (e.g., Material/Wood, Material/Metal) |
| `custom_property_1` | Secondary Asset Classification | AI vision analysis identifies secondary category (e.g., Walnut, Oak, Gold, Chrome) |
| `custom_property_2` | Specific Name/Model of Material | Extracted from filename context or domain knowledge (e.g., Carrera, Verde marina) |
| `custom_property_3` | Style or era classification | AI vision analysis identifies design style (e.g., Modern, Contemporary) |
| `custom_property_4` | Primary color | AI vision analysis extracts dominant color from image (e.g., Beige, Yellow, Teal) |
| `custom_property_5` | - | Unused |
| `custom_property_6` | Dimensions or scale classification | Extracted from metadata or AI scale estimation (e.g., 300x300mm) |
| `custom_property_7` | Reserved | Unused |
| `custom_property_8` | Reference code | OCR extracted from schedule specifications, filename (e.g., AL-01, GL-02) |
| `custom_property_9` | Reserved | Unused |

### Layouts

| Custom Property | Description | Enrichment Method |
|---|---|---|
| `custom_property_0` | Primary asset classification | AI determines leaf subject phrase, prefixed with asset category root (e.g., Layout_Ushape Config, Layout_Lshape Sofa Set) |
| `custom_property_1` | Asset inside the thumbnail | AI looks at image and sees what object is inside, then lists it (e.g., Armchair, Coffee table, Lamp) |
| `custom_property_2` | Usage context or location | AI reasoning determines appropriate usage context (e.g., Living Room, Bedroom) |
| `custom_property_3` | - | Unused |
| `custom_property_4` | - | Unused |
| `custom_property_5` | Reserved | Unused |
| `custom_property_6` | Reserved | Unused |
| `custom_property_7` | Reserved | Unused |
| `custom_property_8` | Reference code | OCR extracted from schedule specifications, filename (e.g., AL-01, GL-02) |
| `custom_property_9` | Reserved | Unused |

### People

| Custom Property | Description | Enrichment Method |
|---|---|---|
| `custom_property_0` | Primary asset classification | AI determines leaf subject phrase, prefixed with person's pose (e.g., People/Standing, People/Sitting) |
| `custom_property_1` | Gender | AI vision analysis image, filename, sidecar (e.g., Male, Female) |
| `custom_property_2` | Ethnicity | AI vision analysis image, filename, sidecar (e.g., Asian, Caucasian) |
| `custom_property_3` | Usage context or location | AI vision analysis image, filename, sidecar (e.g., Living Room, Bedroom) |
| `custom_property_4` | Reserved | Unused |
| `custom_property_5` | Reserved | Unused |
| `custom_property_6` | Reserved | Unused |
| `custom_property_7` | Reserved | Unused |
| `custom_property_8` | Reference code | OCR extracted from schedule specifications, filename (e.g., AL-01, GL-02) |
| `custom_property_9` | Reserved | Unused |

### VFX

| Custom Property | Description | Enrichment Method |
|---|---|---|
| `custom_property_0` | Primary asset classification | AI determines leaf subject phrase, prefixed with asset category root (e.g., VFX/Water, VFX/Smoke, VFX/FallingLeaf) |
| `custom_property_1` through `custom_property_9` | Reserved | Unused |

---

## Canonical EFU Headers

The EFU file must use these exact headers in this order:

```
Filename, Rating, Tags, URL, Comment, ArchiveFile, SourceMetadata, Content Status,
CRC-32, custom_property_0, custom_property_1, custom_property_2, custom_property_3,
custom_property_4, custom_property_5, custom_property_6, custom_property_7,
custom_property_8, custom_property_9
```

---

## Legacy Taxonomy Notes

Legacy prefix-code and static subcategory-table workflows are obsolete. Subject is now produced by the AI model for all asset types, then prefixed with the asset root during ingestion.

**Note:** Everything Search treats property names as case-insensitive in CSV headers. One-meaning-per-column semantic rule enforced (though the meaning changes per asset type).

*End of document.*
