# Everything Search Metadata Columns

Reference for all available metadata columns in `.metadata.efu`. Defines column names, data types, and semantic mappings for core fields, categorization, descriptive attributes, and custom properties.

## Asset Type Column Usage Matrix

| Category | Subject | Title | Company | Album | Author | Period | Color (cp_0) | Location (cp_1) | Form (cp_2) | Chinese (cp_3) | Latin (cp_4) | Size (cp_5) | Code (cp_6) | Finish (cp_7) |
|----------|---------|-------|---------|-------|--------|--------|--------------|-----------------|-----------|---|---|--|--|--|
| **Furniture** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| **Fixture** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| **Vegetation** | ✓ | ✓ | ✓ | — | — | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | — | — |
| **Object** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| **Material** | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | — | ✓ | — | — | ✓ | — | — |
| **Vehicle** | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | — | — | — | — | ✓ | — | — |
| **Layouts** | ✓ | — | — | ✓ | — | — | — | ✓ | ✓ | — | — | ✓ | — | — |
| **People** | ✓ | — | — | — | — | ✓ | ✓ | ✓ | — | — | — | — | — | — |
| **VFX** | ✓ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **Schedule** | ✓ | ✓ | ✓ | — | ✓ | — | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ |

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

**Subject** : Asset classification (primary categorization field) — AI determines the leaf subject phrase, and ingestion stores it as `AssetType/<AI subject>`
- **Furniture**: Examples: `Furniture/Armchair`, `Furniture/Coffee Table`, `Furniture/Bookcase`, `Furniture/Carpet`
- **Fixture**: Examples: `Fixture/Table Lamp`, `Fixture/Pendant Light`, `Fixture/Bathroom Fixture`, `Fixture/Kitchen Faucet`
- **Vegetation**: Examples: `Vegetation/Conifer Tree`, `Vegetation/Flower Shrub`, `Vegetation/Cactus`, `Vegetation/Groundcover`
- **Layouts**: Examples: `Layouts/Bar Table`, `Layouts/Bed Set`, `Layouts/Dining Table`, `Layouts/Seating Lounge`
- **Object**: Examples: `Object/Vase`, `Object/Cushion`, `Object/Book`, `Object/Sculpture`
- **Material**: Examples: `Material/Wood Veneer`, `Material/Brushed Steel`, `Material/Porcelain Tile`, `Material/White Marble`
- **Vehicle**: Examples: `Vehicle/Car`, `Vehicle/Aircraft`, `Vehicle/Boat`, `Vehicle/Ship`
- **VFX**: Examples: `VFX/Fire`, `VFX/Smoke`, `VFX/Water`, `VFX/Sky`
- **People**: Examples: `People/Standing Person`, `People/Sitting Person`, `People/Walking Person`, `People/Group`
- **Schedule**: Examples: `Material/Tile`, `Material/Metal`, `Material/Glass`, `Material/Stone`

**Title** : Model name/designer name. Examples:
- **Furniture**: Model name. Examples: `Barcelona`, `Vernis Blend`, `Eames Lounge`
- **Fixture**: Model name. Examples: `Arco`, `Yoko`, `Tolomeo`
- **Object**: Model name. Examples: `Sahal`, `Bonbori`
- **Vehicle**: Model. Examples: `Model S`, `Boeing 747`, `Yacht`
- **Material**: Material/finish name. Examples: `White Marble`, `Brushed Steel`, `Oak Wood`, `Porcelain Tile`
- **Schedule**: Model/spec name from schedule. Examples: `HMW-6040`, `Timbrium PVDF`, `Type A`

**Album** : Collection / Model
- **Furniture**: Collection. Examples: `Vernis Collection`, `Arco Collection`
- **Fixture**: Collection. Examples: `Arco Collection`
- **Object**: Collection. Examples: `Sahal Collection`

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
- **Schedule**: Client name. Examples: `Wang On`, `Henderson Land`

**Author** : Vendor/company name or source
- **Furniture**: Vendor. Examples: `Dimensiva`, `Design Connected`
- **Fixture**: Vendor. Examples: `Dimensiva`, `Design Connected`
- **Object**: Vendor. Examples: `Dimensiva`, `3dsky`
- **All**: Source origin company
- **Schedule**: Project name. Examples: `Ming Fung Street`, `Lohas Park Phase 3`


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
- **Schedule**: Color from spec. Examples: `White`, `Clear`, `Natural`, `Black`

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

**Code** (custom_property_6) : Material or reference code identifier
- **Schedule**: Material code from spec. Examples: `AL-01`, `GL-02`, `ST-03`, `TL-01`

**Finish** (custom_property_7) : Surface finish or treatment
- **Schedule**: Finish from spec. Examples: `Matt`, `Polished`, `Brushed`, `Sandblasted`, `Powder Coated`, `Anodised`

**Location** (custom_property_1) : Usage context, location, or occupancy
- **Furniture**: Usage location. Examples: `Living Room`, `Bedroom`, `Office`, `Outdoor`
- **Vegetation**: Growth location/habitat. Examples: `Aquatic`, `Home Garden`, `Outdoor`, `Lawn`
- **People**: Scene context. Examples: `Office Meeting`, `Home Environment`, `Outdoor Activity`
- **Layouts**: Room type. Examples: `Kitchen`, `Bedroom`, `Living Room`, `Dining Room`
- **Fixture**: Usage location. Examples: `Bathroom`, `Kitchen`, `Office`, `Living Room`
- **Object**: Usage location. Examples: `Kitchen`, `Bathroom`, `Office`, `Dining Room`
- **Schedule**: Room or area from spec. Examples: `Lobby`, `Master Bathroom`, `Kitchen`, `Facade`

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
- `custom_property_6` = **Code** — Material or reference code identifier (schedule)
- `custom_property_7` = **Finish** — Surface finish or treatment (schedule)
- `custom_property_8-9` — Reserved/unused

**Note:** Everything Search treats property names as case-insensitive in CSV headers. One-meaning-per-column semantic rule enforced.

---

## Legacy Taxonomy Notes

Legacy prefix-code and static subcategory-table workflows are obsolete for `Subject` inference. `Subject` is now produced by the AI model for all asset types, then prefixed with the asset root during ingestion.

*End of document.*
