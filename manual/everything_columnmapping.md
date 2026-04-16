# Everything Search Metadata Columns

Reference for all available metadata columns in `.metadata.efu`. Defines column names, data types, and semantic mappings for core fields, categorization, descriptive attributes, and custom properties.

## Asset Type Column Usage Matrix

| Category | Subject | Title | Company | Album | Author | Period | Color (cp_0) | Location (cp_1) | Form (cp_2) | Chinese (cp_3) | Latin (cp_4) | Size (cp_5) |
|----------|---------|-------|---------|-------|--------|--------|--------------|-----------------|-----------|---|---|--|
| **Furniture** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| **Fixture** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| **Vegetation** | ✓ | ✓ | ✓ | — | — | — | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| **Object** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| **Material** | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | — | ✓ | — | — | ✓ |
| **Vehicle** | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | — | — | — | — | ✓ |
| **Layouts** | ✓ | — | — | ✓ | — | — | — | ✓ | ✓ | — | — | ✓ |
| **People** | ✓ | — | — | — | — | ✓ | ✓ | ✓ | — | — | — | — |
| **VFX** | ✓ | — | — | — | — | — | — | — | — | — | — | — |

**Legend:** ✓ = Used | — = Not used | cp = custom_property

---

## Core Fields

**Filename** : Asset filename (read-only, used for matching)  
Examples: `Armchair_BernieBright_4E85EE94.jpg`, `CoffeeTable_Modern_Design.jpg`

**Rating** : Star rating as numeric value (1, 25, 50, 75, 99)  
Examples: `99` (5★), `75` (4★), `50` (3★), `25` (2★), `1` (1★)

**CRC-32** : Checksum of source archive file (read-only)  
Examples: `4E85EE94`, `EA78D53F`, `7F8E867A`

**Comment** : Free-text notes, warnings, status, or additional info
Examples: `Needs texture update`, `Client favorite`, `High priority`, `Pending review`, `CRC mismatch`

**Tags** : Semicolon-delimited keyword list
Examples: 'procedural', 'multibranched', 'forestpack', 'color adjustable'

**Content Status** : Asset lifecycle status or review stage
    Schedule: Examples: `Draft`, `In Review`, `Approved`, `Rejected`, `Final`, 'Ready for Export'

---

## Categorization (Text)

**Subject** : Asset classification (primary categorization field) — uses full hierarchical subcategory paths per `ingest_keywords.md`
- **Furniture**: Full path. Examples: `Furniture/Seating/Armchair`, `Furniture/Table/CoffeeTable`, `Furniture/Storage/Bookcase`, `Furniture/Carpet/Carpet`
- **Fixture**: Full path. Examples: `Fixture/Lighting/TableLamp`, `Fixture/Lighting/PendantLight`, `Fixture/BathroomFixture`, `Fixture/KitchenFaucet`, `Fixture/KitchenAppliance`
- **Vegetation**: Full path. Examples: `Vegetation/Tree/ConiferTree`, `Vegetation/FlowerShrub`, `Vegetation/Cactus`, `Vegetation/Groundcover`, `Vegetation/Plant`
- **Layouts**: Full path. Examples: `Layouts/BarTable`, `Layouts/BedSet`, `Layouts/DiningTable`, `Layouts/Seating/SeatingLounge`
- **Object**: Full path. Examples: `Object/Decor/Vase`, `Object/Decor/Cushion`, `Object/Tableware/Book`, `Object/Decor/Sculpture`, `Object/Tableware/Tableware`
- **Material**: Full path. Examples: `Material/Leather`, `Material/Wood`, `Material/Metal`, `Material/Glass`, `Material/Tile`, `Material/Fabric`, `Material/Stone`
- **Vehicle**: Full path. Examples: `Vehicle/Car`, `Vehicle/Aircraft`, `Vehicle/Boat`, `Vehicle/Ship`, `Vehicle/Space`
- **VFX**: Full path. Examples: `VFX/Fire`, `VFX/Smoke`, `VFX/Water`, `VFX/Sky`, `VFX/Caustics`, `VFX/Pattern`
- **People**: Full path. Examples: `People/Standing`, `People/Sitting`, `People/Walking`, `People/Group`

**Title** : Model name/designer name. Examples:
- **Furniture**: Model name. Examples: `Barcelona`, `Vernis Blend`, `Eames Lounge`
- **Fixture**: Model name. Examples: `Arco`, `Yoko`, `Tolomeo`
- **Object**: Model name. Examples: `Sahal`, `Bonbori`
- **Vehicle**: Model. Examples: `Model S`, `Boeing 747`, `Yacht`
- **Material**: Material/finish name. Examples: `White Marble`, `Brushed Steel`, `Oak Wood`, `Porcelain Tile`

**Album** : Collection
- **Furniture**: Collection. Examples: `Vernis Collection`, `Arco Collection`
- **Fixture**: Collection. Examples: `Arco Collection`
- **Object**: Collection. Examples: `Sahal Collection`
- **Schedule**: Collection/series. If stated in spec, else `-`. Examples: `Standard`, `Premium`

**ChineseName** (custom_property_3) : Chinese Name Scientific for Vegetation
- **Vegetation**: Chinese Scientific name. Examples: `栎树`, `月季`, `仙人掌`, `地被植物`

**LatinName** (custom_property_4) : Latin/Scientific Name for Vegetation
- **Vegetation** : Latin/Scientific name. Examples: `Quercus robur`, `Rosa damascena`, `Opuntia ficus-indica`, `Pachysandra terminalis`

**Company** : Brand/designer or secondary identifier
- **Furniture**: Brand. Examples: `BBItalia`, `Herman Miller`, `Vitra`
- **Vegetation**: Optional latin name. Examples: `Quercus robur`, `Rosa damascena`
- **Fixture**: Brand. Examples: `Flos`, `Foscarini`, `Artemide`, `Hansgrohe`
- **Object**: Brand. Examples: `Kartell`, `Alessi`
- **Vehicle**: Brand. Examples: `BMW`, `Boeing`, `Ferrari`
- **Material**: Brand/Manufacturer. Examples: `Armani`, `Loro Piana`

**Author** : Vendor/company name or source
- **Furniture**: Vendor. Examples: `Dimensiva`, `Design Connected`
- **Fixture**: Vendor. Examples: `Dimensiva`, `Design Connected`
- **Object**: Vendor. Examples: `Dimensiva`, `3dsky`
- **All**: Source origin company


---

## Descriptive (Vision)

**Size** (custom_property_5) : Dimensions or scale classification
- **Furniture**: Size. Examples: `300x300mm`, `1200x450x350mm`, `Large`
- **Vegetation**: Size. Examples: `3m`, `Small`, `Medium`
- **Fixture**: Size. Examples: `300x300mm`, `450x450mm`
- **Vehicle**: Size. Examples: `1800mm length`, `Compact`
- **Schedule**: Size. Examples: `450x450x200mm`, `As Shown`

**Color** (custom_property_0) : Primary color/material
- **Furniture**: Primary color/material. Examples: `Chrome`, `Matte Black`, `Wood`, `Leather`
- **Vegetation**: Primary color/material. Examples: `Green`, `Autumn Red`, `Golden Yellow`
- **People**: Primary color/material. Examples: `Black Suit`, `Blue Shirt`, `Red Dress`
- **Material**: Primary color/material. Examples: `White`, `Beige`, `Charcoal`, `Natural Oak`
- **Fixture**: Primary color/material. Examples: `Chrome`, `Opal Glass`, `Brushed Steel`
- **Object**: Primary color/material. Examples: `Ceramic`, `Glass`, `Fabric`
- **Vehicle**: Primary color/material. Examples: `Black`, `Silver Metallic`, `Red`

**Period** : Style, era, or temporal classification
- **Furniture**: Style. Examples: `Modern`, `Contemporary`, `Mid-Century`, `Industrial`
- **People**:  Style. Examples: `Contemporary`, `Vintage`, `Formal`
- **Material**: Style. Examples: `Modern`, `Contemporary`, `Mid-Century`, `Industrial`, `Classic`, `Rustic`
- **Fixture**: Style. Examples: `Modern`, `Industrial`, `Scandinavian`
- **Object**:  Style. Examples: `Modern`, `Contemporary`, `Mid-Century`, `Industrial`
- **Vehicle**: Year. Examples: `2024`, `1960`, `Contemporary`

**Form** (custom_property_2) : Shape, form, or physical configuration
- **Layouts**: Layout shape. Examples: `Circle`, `L-shape`, `U-shape`, `Galley`
- **Furniture**: Shape/form. Examples: `Round`, `Rectangular`, `Wall-mounted`, `Freestanding`
- **Vegetation**: Growth form. Examples: `Columnar`, `Conical`, `Spreading`, `Spherical`
- **Material**: Texture pattern/surface finish. Examples: `Diamond`, `Mosaic`, `Square`, `Cross-hatch`, `Smooth`, `Textured`
- **Fixture**: Shape/form. Examples: `Wall-mounted`, `Floor-standing`, `Built-in`
- **Object**: Shape/form. Examples: `Round`, `Rectangular`, `Abstract`

**Location** (custom_property_1) : Usage context, location, or occupancy
- **Furniture**: Usage location. Examples: `Living Room`, `Bedroom`, `Office`, `Outdoor`
- **Vegetation**: Growth location/habitat. Examples: `Aquatic`, `Home Garden`, `Outdoor`, `Lawn`
- **People**: Scene context. Examples: `Office Meeting`, `Home Environment`, `Outdoor Activity`
- **Layouts**: Room type. Examples: `Kitchen`, `Bedroom`, `Living Room`, `Dining Room`
- **Fixture**: Usage location. Examples: `Bathroom`, `Kitchen`, `Office`, `Living Room`
- **Object**: Usage location. Examples: `Kitchen`, `Bathroom`, `Office`, `Dining Room`
- **Schedule**: Location. Examples: `Kitchen`, `Master Bathroom`, `Storage Cabinet`

---

## Unused
- `writer` - Reserved (formerly Vendor/source)
- `artist` - Reserved 
- `language` - Language code
- `copyright` - Copyright information
- `camera-make` - Camera manufacturer
- `camera-model` - Camera model
- `lens-model` - Lens model
- `To` - Reserved
- `From` - Reserved



### Date/Time Properties (String Format)
- `date-modified` - Last modified date
- `date-created` - Creation date
- `date-accessed` - Last accessed date
- `date-taken` - Photo taken date


### Custom Properties (String, 10 Slots)
**Semantic Mapping** (used by `ingest_asset.py`):
- `custom_property_0` = **Color** — Primary color/material color
- `custom_property_1` = **Location** — Usage context/location/habitat
- `custom_property_2` = **Form** — Shape/form/physical configuration
- `custom_property_3` = **ChineseName** — Chinese/scientific name (vegetation)
- `custom_property_4` = **LatinName** — Latin/scientific name (vegetation)
- `custom_property_5` = **Size** — Size or dimensions
- `custom_property_6-9` — Reserved/unused

**Note:** Everything Search treats property names as case-insensitive in CSV headers. One-meaning-per-column semantic rule enforced.

---

## Active Prefix Codes

See [manual/ingest_keywords.md](manual/ingest_keywords.md) for current prefix code mappings (10-xx, 11-xx, 12-xx, 14-xx, 15-xx). The file is source-of-truth for all active category codes and subcategory paths.

*End of document.*

