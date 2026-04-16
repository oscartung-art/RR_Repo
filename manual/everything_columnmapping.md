# Everything Search Metadata Columns

Reference for all available metadata columns in `.metadata.efu`. Use with the clipboard tagger: `columnname:<value> filename.jpg`

---

## Column Usage Overview

| Column | Usage | Status |
|--------|-------|--------|
| Filename | Asset filename matching | Sparse (~1.5%) |
| Rating | Star ratings (1,25,50,75,99) | Sparse (~5%) |
| Tags | Keyword list | Empty |
| URL | URL/project codes | Light (~15%) |
| From | Source origin | Empty |
| **Subject** | **Primary asset classification** | **Heavy (100%)** |
| Title | Designer/model/descriptor | Heavy (95%+) |
| Writer | Brand/designer | Heavy (85%+) |
| Album | Collection/series | Light (~20%) |
| Genre | Color/material/finish | Heavy (90%+) |
| People | Location/context | Moderate (60-70%) |
| Company | Brand/form/shape | Moderate (50-60%) |
| Period | Style/era/temporal | Sparse (~5%) |
| Scale | Size/dimension | Sparse (~10%) |
| Author | Name/identifier | Sparse (~10%) |
| Comment | Notes/status | Light (~15%) |
| To | Recipient | Empty |
| Manager | Category owner | Heavy (100%) |
| CRC-32 | Archive checksum | Heavy (100%) |

---

## Core Fields

**Filename** : Asset filename (read-only, used for matching)  
Examples: `Armchair_BernieBright_4E85EE94.jpg`, `CoffeeTable_Modern_Design.jpg`

**Rating** : Star rating as numeric value (1, 25, 50, 75, 99)  
Examples: `99` (5★), `75` (4★), `50` (3★), `25` (2★), `1` (1★)

**CRC-32** : Checksum of source archive file (read-only)  
Examples: `4E85EE94`, `EA78D53F`, `7F8E867A`

---

## Categorization

**Subject** : Asset classification (primary categorization field) — uses full hierarchical subcategory paths per `ingest_keywords.md`
- **Furniture**: Full path. Examples: `Furniture/Seating/Armchair`, `Furniture/Table/CoffeeTable`, `Furniture/Storage/Bookcase`
- **Fixture**: Full path. Examples: `Fixture/Lighting/TableLamp`, `Fixture/Lighting/PendantLight`, `Fixture/BathroomFixture`, `Fixture/KitchenFaucet`
- **Vegetation**: Full path. Examples: `Vegetation/Tree/ConiferTree`, `Vegetation/FlowerShrub`, `Vegetation/Cactus`, `Vegetation/Groundcover`
- **Building**: Full path. Examples: `Building/Door`, `Building/Window`, `Building/Railing`, `Building/Facade`, `Building/Roof`
- **Layouts**: Full path. Examples: `Layouts/BarTable`, `Layouts/BedSet`, `Layouts/DiningTable`, `Layouts/Seating/SeatingLounge`
- **Object**: Full path. Examples: `Object/Decor/Vase`, `Object/Decor/Cushion`, `Object/Tableware/Book`, `Object/Decor/Sculpture`
- **Procedural**: Full path. Examples: `Procedural/Railing`, `Procedural/CurtainWall`, `Procedural/Roof`, `Procedural/Planter`
- **Vehicle**: Full path. Examples: `Vehicle/Car`, `Vehicle/Aircraft`, `Vehicle/Boat`, `Vehicle/Ship`, `Vehicle/Space`
- **VFX**: Full path. Examples: `VFX/Fire`, `VFX/Smoke`, `VFX/Water`, `VFX/Sky`, `VFX/Caustics`, `VFX/Pattern`
- **People**: Activity/pose context (free-text). Examples: `Standing`, `Sitting`, `Walking`
- **Location**: Category/context (free-text). Examples: `Urban`, `Nature`, `Interior`, `Landscape`, `Environment`

**Title** : Primary descriptor or designer (varies by category)
- **Furniture**: Model name. Examples: `Barcelona`, `Vernis Blend`, `Eames Lounge`
- **People**: Gender. Examples: `Male`, `Female`
- **Fixture**: Model name. Examples: `Arco`, `Yoko`, `Tolomeo`
- **Object**: Model name. Examples: `Sahal`, `Bonbori`
- **Procedural**: Description
- **Vehicle**: Model. Examples: `Model S`, `Boeing 747`, `Yacht`

**Scale** : Size, scale, or dimensional identifier
- **Furniture**: Size. Examples: `300x300mm`, `1200x450x350mm`, `Large`
- **Vegetation**: Size. Examples: `3m`, `Small`, `Medium`
- **People**: Pose / Activity. Examples: `Standing`, `Sitting`, `Walking`
- **Buildings**: Size
- **Fixture**: Size. Examples: `300x300mm`, `450x450mm`
- **Vehicle**: Size. Examples: `1800mm length`, `Compact`
- **Schedule**: Dimension. Examples: `450x450x200mm`, `As Shown`

**Genre** : Color, material, finish, or aesthetic quality
- **Furniture**: Primary color/material. Examples: `Chrome`, `Matte Black`, `Wood`, `Leather`
- **Vegetation**: Foliage color. Examples: `Green`, `Autumn Red`, `Golden Yellow`
- **People**: Clothing color. Examples: `Black Suit`, `Blue Shirt`, `Red Dress`
- **Material**: Dominant color. Examples: `White`, `Beige`, `Charcoal`
- **Fixture**: Primary color/material. Examples: `Chrome`, `Opal Glass`, `Brushed Steel`
- **Object**: Primary color/material. Examples: `Ceramic`, `Glass`, `Fabric`
- **Location**: Height. Examples: `Urban Core`, `Elevated`, `Ground Level`
- **Vehicle**: Color. Examples: `Black`, `Silver Metallic`, `Red`
- **VFX**: Style/variant. Examples: `Turbulent`, `Smooth`, `Particle-based`
- **Schedule**: Finish/color. Examples: `Brushed Bronze PVD`, `Matte Black`, `Satin Stainless Steel`

---

## Descriptive

**Period** : Style, era, or temporal classification
- **Furniture**: Style period. Examples: `Modern`, `Contemporary`, `Mid-Century`, `Industrial`
- **Vegetation**: Seasonal appearance. Examples: `Evergreen`, `Deciduous`, `Spring Blooming`
- **People**: Clothing style. Examples: `Contemporary`, `Vintage`, `Formal`
- **Material**: Material category. Examples: `Stone`, `Metal`, `Textile`
- **Buildings**: Primary material. Examples: `Concrete`, `Glass`, `Steel`
- **Fixture**: Style. Examples: `Modern`, `Industrial`, `Scandinavian`
- **Object**: Style (optional)
- **Layouts**: Layout shape. Examples: `Circle`, `L-shape`, `U-shape`, `Galley`
- **Location**: Custom/context (optional)
- **Vehicle**: Year. Examples: `2024`, `1960`, `Contemporary`
- **Schedule**: Style. Examples: `Modern`, `Contemporary`, or `-`

**Album** : Collection, series, group, or batch identifier
- **Furniture**: Collection. Examples: `Vernis Collection`, `Arco Collection`
- **Vegetation**: Common name. Examples: `Oak Tree`, `Rose`, `Bamboo`
- **People**: Age group. Examples: `20-30`, `40-50`, `Child`
- **Fixture**: Collection. Examples: `Arco Collection`
- **Object**: (varies)
- **Layouts**: (varies)
- **Schedule**: Collection/series. If stated in spec, else `-`. Examples: `Standard`, `Premium`

**Company** : Brand, manufacturer, publisher, or form factor
- **Furniture**: Shape/form. Examples: `Round`, `Rectangular`, `Wall-mounted`, `Freestanding`
- **Vegetation**: Growth form. Examples: `Columnar`, `Conical`, `Spreading`, `Spherical`
- **Material**: Texture pattern. Examples: `Diamond`, `Mosaic`, `Square`, `Cross-hatch`
- **Buildings**: Physical form. Examples: `Load-bearing`, `Modular`, `Structural`
- **Fixture**: Shape/form. Examples: `Wall-mounted`, `Floor-standing`, `Built-in`
- **Object**: Shape/form. Examples: `Round`, `Rectangular`, `Abstract`
- **Layouts**: (none)
- **Location**: Custom/context (optional)
- **Procedural**: Software/plugin. Examples: `Railclone`, `Forest Pack`, `Rhino`

**Writer** : Brand, designer, or secondary descriptor
- **Furniture**: Brand. Examples: `BBItalia`, `Hansgrohe`, `Herman Miller`
- **Vegetation**: Latin/scientific name. Examples: `Quercus robur`, `Rosa damascena`
- **People**: Ethnicity. Examples: `Caucasian`, `Asian`, `Mixed`
- **Fixture**: Brand. Examples: `Flos`, `Foscarini`, `Artemide`, `Hansgrohe`
- **Object**: Brand. Examples: `Kartell`, `Alessi`, `Vitra`
- **Layouts**: Approx. size. Examples: `Small`, `Medium`, `Large`, `2x3m`
- **Location**: Width. Examples: `100m`, `Narrow`, `Wide`
- **Vehicle**: Brand. Examples: `BMW`, `Boeing`, `Ferrari`
- **Schedule**: Brand. Examples: `Hansgrohe`, `Kumeis`, `Hailo`

**Author** : Product name, vendor, or primary identifier
- **Furniture**: Vendor name. Examples: `Dimensiva`, `Design Connected`
- **Fixture**: Vendor name. Examples: `Dimensiva`, `Design Connected`
- **Object**: Vendor name
- **Schedule**: Project code. Examples: `PLS`, `KIL`, `MWR`

---

## Context & Location

**From** : Source origin, provider, or reference
- Used across all categories. Examples: `Design Connected`, `TurboSquid`, `3D Warehouse`, `Archive`

**People** : Usage context, location, or occupancy
- **Furniture**: Usage location. Examples: `Living Room`, `Bedroom`, `Office`, `Outdoor`
- **Vegetation**: Growth location/habitat. Examples: `Aquatic`, `Home Garden`, `Outdoor`, `Lawn`
- **People**: Scene context. Examples: `Office Meeting`, `Home Environment`, `Outdoor Activity`
- **Layouts**: Room type. Examples: `Kitchen`, `Bedroom`, `Living Room`, `Dining Room`
- **Fixture**: Usage location. Examples: `Bathroom`, `Kitchen`, `Office`, `Living Room`
- **Object**: Usage location. Examples: `Kitchen`, `Bathroom`, `Office`, `Dining Room`
- **Location**: Location/context. Examples: `Downtown`, `Suburban`, `Rural`, `Indoor`
- **Schedule**: Location. Examples: `Kitchen`, `Master Bathroom`, `Storage Cabinet`

**Manager** : Category, ownership, project assignment, or responsibility
- **Furniture**: `Furniture`
- **Vegetation**: `Vegetation`
- **People**: `People`
- **Material**: `Material` or `Texture`
- **Buildings**: `Buildings`
- **Layouts**: `Layouts`
- **Fixture**: `Fixture`
- **Object**: `Object`
- **Procedural**: `Procedural`
- **Location**: `Location`
- **Vehicle**: `Vehicle`
- **VFX**: `VFX`
- **Schedule**: `Schedule`
- **Projects**: `Project-<code>` (e.g. `Project-MLS`, `Project-KIL`)

**Comment** : Free-text notes, warnings, status, or additional info
- Examples: `Needs texture update`, `Client favorite`, `High priority`, `Pending review`, `CRC mismatch`

**Tags** : Semicolon-delimited keyword list for search/filtering
- Furniture examples: `modern;black;leather;designer`, `outdoor;seating;weather-resistant`
- Material examples: `stone;natural;textured`, `metal;reflective;industrial`
- Vegetation examples: `native;perennial;drought-resistant`, `tropical;ornamental`

**URL** : Associated URL, reference, product page, or project code
- **Furniture/Fixture**: Product page. Example: `https://www.dimensiva.com/product/vernis-blend`
- **Object**: Product page
- **Schedule**: Item reference ID. Example: `KF-01`, `SF-03` (repurposed from URL field)

**To** : Destination, recipient, or target audience
- Examples: `Client XYZ`, `Archive`, `Production`, `QA Review`, `Final Export`

---

## Usage with Clipboard Tagger

Format: `columnname:<value> filename.jpg | file2.jpg`

**Examples across categories:**
- `rating:<99> Armchair.jpg` — Set 5-star rating
- `subject:<Furniture/Seating/Armchair> file1.jpg | file2.jpg` — Set furniture hierarchy
- `subject:<Tree> Plant.jpg` — Set vegetation type
- `author:<Rossin> Armchair.jpg` — Set designer/model name
- `genre:<Black Leather> Armchair.jpg` — Set material/color
- `period:<Modern> Table.jpg` — Set style period
- `album:<MoMA Collection> file.jpg` — Set collection name
- `company:<Round> Table.jpg` — Set shape/form
- `people:<Living Room> Sofa.jpg` — Set usage location
- `comment:<Needs texture check> asset.jpg` — Add notes

**Delete command:**
- `delete: file1.jpg | file2.jpg | file3.jpg` — Remove entries + images + archives
- `subject` - Asset classification field
- `author` - Custom semantic field
- `writer` - Custom semantic field
- `album` - Custom semantic field
- `genre` - Custom semantic field
- `people` - Custom semantic field
- `company` - Custom semantic field
- `period` - Custom semantic field
- `artist` - Custom semantic field
- `title` - Custom semantic field
- `comment` - Custom semantic field
- `url` - URL field
- `from` - Custom semantic field
- `manager` - Identifier/reference

### Date/Time Properties (String Format)
- `date-modified` - Last modified date
- `date-created` - Creation date
- `date-accessed` - Last accessed date
- `date-taken` - Photo taken date

### Media/Document Properties (String)
- `language` - Language code
- `copyright` - Copyright information
- `camera-make` - Camera manufacturer
- `camera-model` - Camera model
- `lens-model` - Lens model

### Custom Properties (String, 10 Slots)
- `custom-property-0`
- `custom-property-1`
- `custom-property-2`
- `custom-property-3`
- `custom-property-4`
- `custom-property-5`
- `custom-property-6`
- `custom-property-7`
- `custom-property-8`
- `custom-property-9`

**Note:** Everything treats property names as case-insensitive in CSV headers.

### Old Index Lookup
00 index
01-00 inbox
01-01 general inbox
02-00 notes
02-01 general notes
02-02 list
02-03 table(graph)
02-04 checklist
02-05 quotation
03-00 work files
04 bookmarks
05 templates
06-00 status
06-01 working
06-02 completed
06-03 rejected
06-04 selected
06-05 signed
06-06 sent
06-07 temporary
06-08 pending-selection
06-09 pending start
06-10 model named
06-11 model thumbnail ready
06-12 model 3d ready
06-20 model diffuse ready
06-30 rendering draft max screen cap
06-50 -
06-61 paid
06-62 delivered
06-63 installed
07-00 outbox
07-01 shared
07-02 accounting
08
09 archive
10-00 -- furniture --
10-01 bench
10-02 carpet
10-03 chair
10-04 curtain
10-05 sofa-2-seater
10-06 sofa
10-07 sofa armchair
10-08 sofa pouf
10-09 sofa ottoman
10-10 stool
10-11 stool bar
10-12 table single
10-13 table coffee
10-14 table console
10-15 table desk
10-16 table side
10-17 cabinet
10-17-B cabinet-bathroom
10-17-O cabinet office
10-17-S cabinet set
10-18 cabinet bookcase
10-19 cabinet tv
10-20 table others
10-21 daybed
10-22 bed
10-23 closet
10-24 bedside table
10-25 shelving
10-26 table dresser
10-27 armchair exterior
10-28 bench exterior
10-29 barstool exterior
10-30 chair exterior
10-37 lounger outdoor
10-38 parsole outdoor
10-39 sofa exterior
10-40 table side u shape
10-41 sofa hanging
10-42 table exterior
10-43 table office
10-44 table set
10-45 table chair set
10-46 coffee & side table set
10-47 -
10-48
10-49
10-50 chair-rattan
10-51
10-52
10-53
10-54
10-55
10-56
10-57
10-58
10-59
10-60 -- office furniture --
10-63 storage office
10-64 sofa office
10-65
10-65 chair office
10-66
10-67
10-68
10-69
10-70 -- kidsroom unsorted --
10-71 chair kidsroom
10-72
10-73
10-74
10-75
10-76
10-77
10-78
10-79
11-00 -- arch --
11-01 canopy
11-02 ceiling
11-03 door
11-04 E&M
11-05 facade
11-06 fence
11-07 floor
11-08 gate
11-09 ironmongrey
11-10 louver
11-11 profile
11-12 assembly equipment
11-13 railing
11-14 roof
11-15 screen
11-16 spandrel
11-17 wall
11-18 window
11-19
11-20
11-21
11-21 appliances
11-22
11-23
11-24
11-25
11-26
11-27
11-28
11-29
11-30
11-30 -
11-31 appliances bathroom
11-32 fixture bathroom (cabinet, hangers..etc)
11-33 plumbing bathroom (basin,
11-34
11-35
11-36
11-37
11-38
11-39
11-40
11-40 kitchen unsorted
11-41 kitchen appliance
11-42 kitchen fixture
11-43 kitchen plumbing
11-44 sink kitchen
11-45 faucet kitchen
11-46 rain shower bathroom
11-47
11-48
11-49
11-50
11-50 -
11-51
11-52
11-53
11-54
11-55
11-56
11-57
11-58
11-59
11-60
11-60 -- indoor --
11-61 office appliances
11-62
11-63
11-64
11-65
11-66
11-67
11-68
11-69
11-70
11-70 -- office --
11-71
11-72
11-73
11-74
11-75
11-76
11-77
11-78
11-79
11-80
11-81
11-82
11-83
11-84
11-85
11-86
11-87
11-88
11-89
11-90
11-91
11-92
11-93
11-94
11-95
11-96
11-97
11-98
11-99
12-00 'decoration unsorted'
12-01 art
12-02 book-single
12-02-H book-stack horizontal
12-02-V book-stack vertical
12-03 bowl
12-04 candle
12-05 clock
12-06 cushion
12-07 display decor
12-08 hobbies
12-09 decor-set-shelving
12-10 music
12-11 sculpture toy
12-12 vase
12-13 wall decor
12-14 mirror
12-15 storage
12-16 tray
12-16-A tray drinks
12-16-B tray food
12-17 frame
12-18 digital
12-20 office decor
12-21 closet-decor
12-22 -
12-23 potted plant single table
12-24 potted plant set table
12-26 potted plant floor set
12-27 planter box set
12-28 green wall set
12-29
12-30 decor kitchen unsorted
12-31 dining tableware
12-32 dining table centerpiece
12-33 dining food single
12-34 dining table tableware
12-35 cookware
12-36 fabric kitchen
12-37 dining drinks set
12-38 decor kitchen set shelve
12-39 food drinks single
12-40 food fruit bowl
12-41 display cabinet tableware
12-42 retail-food-shelve-display
12-43 dining kart
12-44
12-45
12-46
12-47 food display retail
12-48 food wine related
12-49 food cart
12-50 -- kidsroom decor --
12-51 toys
12-52
12-53
12-54
12-55
12-56
12-56 fabric bathroom
12-57
12-58
12-59
12-60 -- bathroom decor --
14-00 'vegetation unsorted'
14-01 groundcover
14-02 grass-wild
14-03 grass-flower
14-04 gravel
14-05 mountain
14-06 plant
14-07 plant aquatic
14-08 plant cactus
14-09 plant crops
14-10 plant dry
14-11 plant flower
14-12 -
14-17 plant succulent
14-18 plant creeper
14-19 plant wild
14-20 rock
14-21 shrub
14-22 shrub flower
14-23 shrub hedge
14-24 tree
14-25 tree bamboo
14-26 tree winter
14-27 tree conifer
14-28 -
14-29 tree flower
14-30 tree large
14-31 -
14-32 tree palm
14-33 tree small
14-34 tree stump
14-35 greenwall forest
14-37 -
14-38 -
14-39 -
14-40 shape
14-41 oval
14-42
14-43
14-44
14-45
14-46
14-47
14-48
14-49
14-50
14-51
14-52
14-53
14-54
14-55
14-56
14-57
14-58
14-59
14-60
14-61
14-62
14-63
14-64
14-65
14-66
14-67
14-68
14-69
14-70
14-71
14-72
14-73
14-74
14-75
14-76
14-77
14-78
14-79
14-80
14-81
14-82
14-83
14-84
14-85
14-86
14-87
14-88
14-89
14-90
14-91
14-92
14-93
14-94
14-95
14-96
14-97
14-98
14-99
15-01 architectural light - Copy
15-02 ceiling light
15-03 chandelier
15-04 floor light
15-05 pendant light (unsorted)
15-06 table light
15-07 wall light
15-08 street light
15-09 lantern
15-09 trough light
15-10
15-10 fill light
15-11
15-11 spotlight accent
15-12
15-12 sky light
15-13
15-13 fake light (spotlight)
15-14
15-15
15-16
15-17
15-18
15-19
15-20 pendant (drum)
15-21 pendant (linear)
15-22 pendant (tiered)
15-23 pendant (star)
15-24 pendant (shaded)
15-25 pendant (waterfall)
15-26 pendant (irregular)
15-27 pendant (orb)
15-28 pendant (caged)
15-29 pendant (wire)
15-30 pendant (crystal)
15-31 pendant (cylinder)
15-32 pendant (branched)
15-33 pendant (sprial)
15-34 pendant (rattan)
15-35 pendant (globe)
15-36 pendant (rectangular)
16 environment
16-00 -- urban --
16-01 facilites urban
16-02 road
16-03 sidewalk
16-04 traffic
16-40 backdrop
16-50 -
17 vfx
17-00 -- people --
17-01 activity
17-02 animal
17-03 business
17-04 interactive
17-05 family
17-06 pool & beach
17-07 casual
17-08
17-09
17-20 -- vehicle --
17-21 aircraft
17-22 boat
17-23 car
17-24 ship
17-25 space
17-30 -- vfx --
18 misc
18-00 -- proxy --
18-01 decor proxy
18-02 structure-proxy
18-03 furniture proxy
18-04 peole proxy
18-04 vegetation proxy
18-10 -- utility --
18-11 shaderball
18-12 pattern
18-13 place holder
18-40 -- furniture set --
18-41 dining table set
18-42 sofa set
18-43 coffee table set
18-44 tableware set
18-56 cusion set
18-57 tray set
19 3d collection
20-00 -- finishes unsorted --
20-01 leather
20-02 velvet
20-03 curtain-sheer
20-04 lampshade
20-05 silk
20-06 weave
20-07 woven
20-08 cotton
20-09 carpet-fabric
20-10 -- metal --
20-11 satin-metal
20-12 glossy-metal
20-13 matte-metal
20-14 hammered-metal
20-15 -
20-16 antique-metal
20-17 painted metal
20-18
20-19
20-20 -- wood --
20-21 veneer & plastic lamiante
20-22 panel
20-23 parquet
20-24
20-25
20-26
20-27
20-28
20-29
20-30 stone ceramic
20-31 stone granite
20-32 stone marble
20-33 stone terrazzo
20-34 stone raw
20-35 stone marble special
20-40 -- paint --
20-41 satin paint
20-42 polished paint
20-43 matte paint
20-44 groute paint
20-50 stone ceramic tile
20-51 city-road
20-52 stone mosaic tile
20-53 paving tile
20-55 -
20-55 stone granite tile
20-56 stone raw tile
20-58
20-60 -- glass --
20-61 clear glass
20-62 frosted glass
20-63 pattern glass
20-64 polished glass
20-65 opague glass
20-66 mirror glass
20-67 tinted-glass
20-70 -- other --
20-71 concrete
20-72 mulch
20-73 pebble
20-74 utility (texture)
20-76 asphalt
20-78 wax
20-79 wallpaper
20-80 multimat
20-81 vinyl
20-82
20-83
20-84
20-85
20-86
21-00 graphics unsorted
21-02 billboard
21-03 bookcover
21-04 monitor
21-05 signage
21-06 carpet-art
21-07 decoration display
21-08 wallpaper
21-09 kitchen appliances
21-20 art
22-00 -- hdr unsorted --
22-01 clear
22-02 cloudy
22-03 overcast
22-04 sunset
22-05 dawn
22-06 studio
22-07 interior
22-08 city
23 cutout
23-00 -- people --
23-01 activity
23-02 animal
23-03 business
23-04 interactive
23-05 family
23-06 pool & beach
23-07 casual
23-08 sitting
23-09 standing
23-10 walking
23-20 -- vegetation --
23-21 plant
23-22 tree
23-23 shrub
23-24 flower-potted-table
24 environment
24-00 -- building --
24-01 bookstore
24-02 apparell
24-03 office
24-04 F&B
24-05 furniture
24-06 grocery
24-07 signage
24-08 skincare
24-09 lifestyle
24-10 electronic
24-11 residential
24-12 floral
24-13 gym
24-14 lobby
24-15 sports
24-16 medical
24-17 art gallery
24-26 plant potted floor
24-30 -- nature --
24-31 bark
24-32 stem
24-33 leaf
24-34 flower
24-35 grass
24-36 green-wall
24-37 fallen-leaves
24-38 fruit texture
24-39
24-40 backplate-texture
24-41 mountain
24-42 sea
24-43 sky
24-44 treeline
24-45 urban
24-46
24-47
24-48
24-49
24-50 -- liquid --
24-51 ocean
24-52 pool
24-53 water
24-54 wine
24-70 -- misc --
24-71 dirt
24-72 section
24-73 reference
25-00 -- misc --
25-01 flame
25-02 smoke
25-03 sky-timelaspe
25-04 caustics
25-05 pattern
25-06 emissive
25-07 unreal-base
25-08 utility
25-09 decal
25-20 still-camera
25-21 animated-camera
25-22 16 to 9 camera
26
27 texture collection
28 hdr collection
29 material collection
30 animation
30-00 -- animation --
30-01 residential
30-02 commercial
30-03 cinemagraph
31 rendering
32 photo
32-01 cabinet styling
32-02 table
32-10 -- vegetation --
32-11 plant
32-12 tree
32-13 grass
32-14 shrub
32-15 greenwall
32-16 planter
32-20 site
33 layout
33-00 -- layout --
33-01 masterplan layout
33-02 unit layout
33-03 landscape layout
34 material
35 mood
36
37
38
39 reference collection
39-01 dbox
39-02 sino
39-03 swire
39-04 shk
40 CAD
40-00 -- typical drawings --
40-01 general CAD
40-02 layout plan
40-03 elevation
40-04 details
40-05 reflected ceiling plan
40-06 demarcation plan
40-07 landscape master plan
40-08 setting out plan
40-09 lighting plan
40-10 demolition plan
40-30 -- GBP --
40-31 GBP floor plan
40-32 GBP elevation
40-33 GBP section
40-35 GBP general notes
40-50 -- GIS --
40-51 iB1000 plan
41 Schedules
41-01 material schedule
41-02 decorative lighting schedule
41-03 lighting schedule
41-04 floor finishes schedule
41-05 furniture schedule
41-06 kitchen appliance schedule
41-07 kitchen fitment schedule
41-08 typical ironmongrey schedule
41-09 typical socket schedule
41-10 door schedule
41-11 sanitary fitment schedule
41-12 window schedule
41-13 louvre schedule
41-14 -
42 Mark-up
42-01 material code mark-up
42-02 camera angle mark-up
42-03 rendering comment markup
42-04 animation path mark-up
43 documents
43-00
43-01 quotation
43-02 invoice
43-03 variation orders
44 presets
44-01 max project folder preset
44-01 npp style preset
44-20 -- unreal --
44-21 MPP movie pipeline primary config
44-22 LS lighting level preset
45 camera
45-01 16-9
45-02 9-16
45-03 4-3
45-04 3-4
45-05 1-1
46
47
48
49
50 incoming
50 to 59 project
50-00 working
50-01 CAD
50-02 3d-model incoming
50-03 schedule
50-04 mark-up
50-05 -
50-06 -
50-07 site photos
50-20 -
50-21 -
50-22 -
50-23 -
50-24 -
50-25 -
50-30
50-31 -
50-32 -
50-33 -
50-34 -
50-35 -
50-36 -
50-40 -- schedule --
50-41 material schedule
50-42 landscape schedule
50-43 window door schedule
50-44 furniture schedule
50-45 lighting schedule
50-46 ironmongrey schedule
50-50 --GIS--
50-51 GIS 3D
50-52 GIS splines
51 working
51-00 -- working --
51-01 3d-asset
51-02 texture
51-03 others
51-04 scene
51-05 backup
51-06 io texture
51-07 render output
51-08 material
51-10 io
51-11 datasmith
51-12 anima
51-13 GIS 3D
51-14 GIS splines
51-15 render passes
51-16 material library
51-17 LS level sequence
51-18 render settings max
51-19 unreal lighting level settings (path tracing)
51-20 unreal lighting level settings
51-21 level
51-22 movie render queue
51-23 movie pipline queue
52 outgoing
52-00
52-01 documents
52-01 fusion
52-02 shared
52-03 final shared
52-04 obselete
53 post
54 presets
54-01 max preset
54-02 sketchup preset
54-03 unreal preset
55 archive
60 computer
60 to 69
61 website
62 company documentation
63 guide
64 reference collection
64-01 dbox
64-02 sino
70
70 to 79 personal
71
72
73
74
75
76
77
78
79
80
80 to 89
81
82
83
84
85
86
87
88
89
90
90 to 99
91
92
93
94
95
96
97
98
99
bedroom bedroom
New folder
potted-plant-floor single