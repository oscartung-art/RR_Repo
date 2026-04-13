# Ingest Keywords
Single source of truth for all keyword tables used by `tools/ingest_asset.py`.
Edit here — the script loads these tables at runtime. Run `tools/audit_keywords.py` to check for collisions, orphans, or duplicates.

## Overview
Main taxonomy categories in this document: 12.
Furniture, Fixture, Vegetation, Material, Object, Vehicle, VFX, Procedural, Layouts, Building, People, Location.
Hierarchical category values should use `/` between levels (for example `Flooring/Carpet`) instead of flattened CamelCase.
For EFU export, the `Mood` column stores the full hierarchy path derived from the allowlist group, for example `Furniture/Seating/LoungeChair`, `Furniture/Table/SideTable`, or `Furniture/Carpet`.

## Table of Contents
1. Furniture
2. Fixture
3. Vegetation
4. Material
5. Object
6. Vehicle
7. VFX
8. Procedural
9. Layouts
10. Building
11. People
12. Location

---

## 1. Furniture
Columns in `Datavalidation.tsv`: `FurnitureName | Category | Color | Brand | Material | Size | Form | Location`.
`Color`, `Brand`, `Material`, `Size` are free-text. `Location` = `Bedroom` (when specified).
Prefix codes `10-xx` map individual Furniture pieces; `15-xx` maps Lighting variants.
In exported EFU rows, `Mood` stores the full hierarchy path, for example `Furniture/Seating/LoungeChair`, `Furniture/Table/SideTable`, or `Furniture/Carpet`.

---

## 2. Fixture
Columns in `Datavalidation.tsv`: `Category | Primary Description | Brand | Material | Form | Location`.
`Brand`, `Material`, `Form` are free-text. `Location` = Bathroom / Bedroom / Kitchen (where applicable).

---

## 3. Vegetation
Columns in `Datavalidation.tsv`: `Category | SubCategory | BotanicalName | ChineseName | Height/Size | Location | Form | Color/Feature | Code | CommonName`.
`BotanicalName`, `ChineseName`, `CommonName`, `Height/Size` are free-text.

Location (Habitat): Aquatic, Crop, Floor, GreenWall, Home, Lawn, Ornamental, Outdoor, PlantPot, PlanterBox, Table, Wetland, Wild
Form: Columnar, Conical, Fan, Feather, GrassLike, Globe, MutiStem, Oval, Pear, Rosette, Spherical, Spreading, TreeForm, Upright
Feature: Deciduous, Dry, Evergreen, Flowering

---

## 4. Material
Columns in `Datavalidation.tsv`: `MaterialName | Category | Color | Finish | Size | Pattern | Location`.
`MaterialName`, `Color`, `Finish`, `Size` are free-text.

Pattern (tile/flooring layout size): Diamond, Jumbo, Mosaic, Ocon, Square

---

## 5. Object
Columns in `Datavalidation.tsv`: `SubCategory | Brand | Material | Form | Location`.
`Brand`, `Material`, `Form` are free-text.

---

## 6. Vehicle
Columns in `Datavalidation.tsv`: `Vehicle`.

Vehicle/Aircraft
Vehicle/Boat
Vehicle/Car
Vehicle/Ship
Vehicle/Space

---

## 7. VFX
Columns in `Datavalidation.tsv`: `VFX`.

VFX/Caustics
VFX/Emissive
VFX/Fire
VFX/Pattern
VFX/Sky
VFX/Smoke
VFX/Water

---

## 8. Procedural
Columns in `Datavalidation.tsv`: `Procedural`.

Procedural/CurtainWall
Procedural/Planter
Procedural/Railing
Procedural/Roof

---

## 9. Layouts
Columns in `Datavalidation.tsv`: `Category | SubCategory | Location | Form`.

Layouts/BarTable
Layouts/BedSet
Layouts/Closet
Layouts/DiningTable
Layouts/Seating/SeatingLounge
Layouts/Seating/SeatingPoolSide

Form: Circle, Galley, Lshape, Oval, Ushape

---

## 10. Building
Columns in `Datavalidation.tsv`: `Category | SubCategory | Width | Length | Height`.
`Width`, `Length`, `Height` are free-text dimensions.

---

## 11. People
Columns in `Datavalidation.tsv`: `Number of people | Age | Ethnicity | Season | Gender | Accessories | Activity | Clothing`.
All values are free-text — no fixed allowlist.

---

## 12. Location
Columns in `Datavalidation.tsv`: `Category | SubCategory | Width | Length | Height | Location | Custom7 | Custom8`.
All values are free-text — no fixed allowlist.

---

## Runtime & Support Tables
Parsed by `tools/ingest_asset.py` at startup. Numbered sections above are human reference only.

---

## Prefix Codes
Maps filename prefix codes (e.g. `10-01`) to canonical CamelCase subcategory names.
Both `10-01` and compact `1001` forms are accepted at ingest time.

| Code    | Subcategory         | Notes                              |
|---------|---------------------|------------------------------------|
| 10-01   | Bench               |                                    |
| 10-02   | Carpet              |                                    |
| 10-03   | Chair               |                                    |
| 10-04   | Curtain             |                                    |
| 10-05   | Sofa                | 2-seater                           |
| 10-06   | Sofa                |                                    |
| 10-07   | Armchair            |                                    |
| 10-08   | Pouf                |                                    |
| 10-09   | Ottoman             |                                    |
| 10-10   | Stool               |                                    |
| 10-11   | Barstool            |                                    |
| 10-12   | DiningTable         |                                    |
| 10-13   | CoffeeTable         |                                    |
| 10-14   | ConsoleTable        |                                    |
| 10-15   | Desk                |                                    |
| 10-16   | SideTable           |                                    |
| 10-17   | Cabinet             |                                    |
| 10-17-B | BathroomCabinet     |                                    |
| 10-17-O | OfficeStorage       |                                    |
| 10-17-S | CabinetSet          |                                    |
| 10-18   | Bookcase            |                                    |
| 10-19   | TVStand             |                                    |
| 10-20   | Table               |                                    |
| 10-21   | Daybed              |                                    |
| 10-22   | Bed                 |                                    |
| 10-23   | Wardrobe            |                                    |
| 10-24   | Nightstand          |                                    |
| 10-25   | ShelvingUnit        |                                    |
| 10-26   | Dresser             |                                    |
| 10-27   | ArmchairOutdoor     |                                    |
| 10-28   | BenchOutdoor        |                                    |
| 10-29   | BarstoolOutdoor     |                                    |
| 10-30   | ChairOutdoor        |                                    |
| 10-37   | SunLounger          |                                    |
| 10-38   | Parasol             |                                    |
| 10-39   | SofaOutdoor         |                                    |
| 10-40   | SideTable           | U-shape                            |
| 10-41   | HangingChair        |                                    |
| 10-42   | TableOutdoor        |                                    |
| 10-43   | OfficeTable         |                                    |
| 10-44   | TableSet            |                                    |
| 10-45   | DiningSet           |                                    |
| 10-46   | CoffeeTableSet      |                                    |
| 10-50   | RattanChair         |                                    |
| 10-63   | OfficeStorage       |                                    |
| 10-64   | OfficeSofa          |                                    |
| 10-65   | OfficeChair         |                                    |
| 10-71   | KidsChair           |                                    |
| 11-01   | Canopy              |                                    |
| 11-02   | Ceiling             |                                    |
| 11-03   | Door                |                                    |
| 11-04   | MEP                 |                                    |
| 11-05   | Facade              |                                    |
| 11-06   | Fence               |                                    |
| 11-07   | FloorElement        |                                    |
| 11-08   | Gate                |                                    |
| 11-09   | Ironmongery         |                                    |
| 11-10   | Louvre              |                                    |
| 11-11   | Profile             |                                    |
| 11-12   | AssemblyEquipment   |                                    |
| 11-13   | Railing             |                                    |
| 11-14   | Roof                |                                    |
| 11-15   | Screen              |                                    |
| 11-16   | Spandrel            |                                    |
| 11-17   | Wall                |                                    |
| 11-18   | Window              |                                    |
| 11-21   | Appliance           |                                    |
| 11-31   | BathroomAppliance   |                                    |
| 11-32   | BathroomFixture     |                                    |
| 11-33   | BathroomPlumbing    | basin, toilet, WC                  |
| 11-41   | KitchenAppliance    |                                    |
| 11-42   | KitchenFixture      |                                    |
| 11-43   | KitchenPlumbing     |                                    |
| 11-44   | KitchenSink         |                                    |
| 11-45   | KitchenFaucet       |                                    |
| 11-46   | RainShower          |                                    |
| 11-61   | OfficeAppliance     |                                    |
| 12-01   | Art                 |                                    |
| 12-02   | Book                |                                    |
| 12-02-H | BookStack           | horizontal stack                   |
| 12-02-V | BookStack           | vertical stack                     |
| 12-03   | Bowl                |                                    |
| 12-04   | Candle              |                                    |
| 12-05   | Clock               |                                    |
| 12-06   | Cushion             |                                    |
| 12-07   | DecorDisplay        |                                    |
| 12-08   | Hobby               |                                    |
| 12-09   | ShelvingDecor       |                                    |
| 12-10   | MusicDecor          |                                    |
| 12-11   | Sculpture           |                                    |
| 12-12   | Vase                |                                    |
| 12-13   | WallDecor           |                                    |
| 12-14   | Mirror              |                                    |
| 12-15   | Storage             |                                    |
| 12-16   | Tray                |                                    |
| 12-16-A | DrinksTray          |                                    |
| 12-16-B | FoodTray            |                                    |
| 12-17   | Frame               |                                    |
| 12-18   | DigitalDecor        |                                    |
| 12-20   | OfficeDecor         |                                    |
| 12-21   | ClosetDecor         |                                    |
| 12-23   | PottedPlantTable    |                                    |
| 12-24   | PottedPlantSet      |                                    |
| 12-26   | FloorPlanter        |                                    |
| 12-27   | PlanterBox          |                                    |
| 12-28   | GreenWall           |                                    |
| 12-31   | Tableware           |                                    |
| 12-32   | TableCenterpiece    |                                    |
| 12-33   | DiningFood          |                                    |
| 12-34   | DiningTableware     |                                    |
| 12-35   | Cookware            |                                    |
| 12-36   | KitchenFabric       |                                    |
| 12-37   | DrinksSet           |                                    |
| 12-39   | FoodDrinks          |                                    |
| 12-40   | FruitBowl           |                                    |
| 12-41   | DisplayTableware    |                                    |
| 12-47   | FoodDisplay         |                                    |
| 12-48   | WineRelated         |                                    |
| 12-49   | FoodCart            |                                    |
| 12-51   | Toy                 |                                    |
| 12-56   | BathroomFabric      |                                    |
| 14-01   | Groundcover         |                                    |
| 14-02   | WildGrass           |                                    |
| 14-03   | FlowerGrass         |                                    |
| 14-04   | Gravel              |                                    |
| 14-06   | Plant               |                                    |
| 14-07   | AquaticPlant        |                                    |
| 14-08   | Cactus              |                                    |
| 14-09   | CropPlant           |                                    |
| 14-10   | DryPlant            |                                    |
| 14-11   | FlowerPlant         |                                    |
| 14-17   | Succulent           |                                    |
| 14-18   | CreeperPlant        |                                    |
| 14-19   | WildPlant           |                                    |
| 14-20   | Rock                |                                    |
| 14-21   | Shrub               |                                    |
| 14-22   | FlowerShrub         |                                    |
| 14-23   | Hedge               |                                    |
| 14-24   | Tree                |                                    |
| 14-25   | BambooTree          |                                    |
| 14-26   | WinterTree          |                                    |
| 14-27   | ConiferTree         |                                    |
| 14-29   | FlowerTree          |                                    |
| 14-30   | LargeTree           |                                    |
| 14-32   | PalmTree            |                                    |
| 14-33   | SmallTree           |                                    |
| 14-34   | TreeStump           |                                    |
| 14-35   | GreenWallForest     |                                    |
| 15-01   | ArchitecturalLight  |                                    |
| 15-02   | CeilingLight        |                                    |
| 15-03   | Chandelier          |                                    |
| 15-04   | FloorLamp           |                                    |
| 15-05   | PendantLight        | unsorted                           |
| 15-06   | TableLamp           |                                    |
| 15-07   | WallLamp            |                                    |
| 15-08   | StreetLight         |                                    |
| 15-09   | Lantern             |                                    |
| 15-10   | FillLight           |                                    |
| 15-11   | SpotlightAccent     |                                    |
| 15-12   | SkyLight            |                                    |
| 15-20   | PendantDrum         |                                    |
| 15-21   | PendantLinear       |                                    |
| 15-22   | PendantTiered       |                                    |
| 15-23   | PendantStar         |                                    |
| 15-24   | PendantShaded       |                                    |
| 15-25   | PendantWaterfall    |                                    |
| 15-26   | PendantIrregular    |                                    |
| 15-27   | PendantOrb          |                                    |
| 15-28   | PendantCaged        |                                    |
| 15-29   | TroughLight         |                                    |
| 15-30   | PendantCrystal      |                                    |
| 15-31   | PendantCylinder     |                                    |
| 15-32   | PendantBranched     |                                    |
| 15-33   | PendantSpiral       |                                    |
| 15-34   | PendantRattan       |                                    |
| 15-35   | PendantGlobe        |                                    |
| 15-36   | PendantRectangular  |                                    |

---

## Keyword Map
Text keywords found in filename stems → canonical subcategory.
Multi-word entries checked before single-word ones (order matters — keep specific before general).

| Keyword              | Subcategory         | Notes |
|----------------------|---------------------|-------|
| coffee table         | CoffeeTable         |       |
| side table           | SideTable           |       |
| dining table         | DiningTable         |       |
| console table        | ConsoleTable        |       |
| low table            | SideTable           |       |
| end table            | SideTable           |       |
| nesting table        | SideTable           |       |
| bar table            | BarTable            |       |
| office table         | OfficeTable         |       |
| bedside table        | BedsideTable        |       |
| display cabinet      | DisplayCabinet      |       |
| tv cabinet           | TvCabinet           |       |
| entertainment center | EntertainmentCenter |       |
| rain shower          | RainShower          |       |
| shower mixer         | ShowerMixer         |       |
| shower head          | ShowerHead          |       |
| floor lamp           | FloorLamp           |       |
| table lamp           | TableLamp           |       |
| wall lamp            | WallLamp            |       |
| ceiling light        | CeilingLight        |       |
| pendant lamp         | PendantLight        |       |
| reading lamp         | ReadingLamp         |       |
| bunk bed             | BunkBed             |       |
| room divider         | RoomDivider         |       |
| lounge chair         | LoungeChair         |       |
| dining chair         | DiningChair         |       |
| office chair         | OfficeChair         |       |
| bar stool            | Barstool            |       |
| bar chair            | Barstool            |       |
| arm chair            | Armchair            |       |
| reclining chair      | RecliningChair      |       |
| massage chair        | MassageChair        |       |
| sectional            | SectionalSofa       |       |
| loveseat             | Loveseat            |       |
| sofa                 | Sofa                |       |
| couch                | Sofa                |       |
| lounger              | Lounger             |       |
| armchair             | Armchair            |       |
| chair                | SideChair           |       |
| bench                | Bench               |       |
| ottoman              | Ottoman             |       |
| nightstand           | Nightstand          |       |
| bedside              | Nightstand          |       |
| desk                 | Desk                |       |
| table                | SideTable           |       |
| lamp                 | TableLamp           |       |
| chandelier           | Chandelier          |       |
| pendant              | PendantLight        |       |
| platter              | ServingPlatter      |       |
| bowl                 | Bowl                |       |
| vase                 | Vase                |       |
| tray                 | Tray                |       |
| mirror               | Mirror              |       |
| carpet               | Carpet              |       |
| rug                  | Carpet              |       |
| curtain              | Curtain             |       |
| roller blind         | CurtainBlind        |       |
| blind                | Curtain             |       |
| billiard             | Billiard            |       |
| wardrobe             | Wardrobe            |       |
| closet               | Wardrobe            |       |
| shelf                | ShelvingUnit        |       |
| shelving             | ShelvingUnit        |       |
| bookcase             | Bookcase            |       |
| sideboard            | Sideboard           |       |
| dresser              | Dresser             |       |
| credenza             | Credenza            |       |
| drawer chest         | DrawerChest         |       |
| divan                | Divan               |       |
| cabinet              | Cabinet             |       |
| daybed               | Daybed              |       |
| futon                | Futon               |       |
| bed                  | Bed                 |       |
| bathtub              | Bathtub             |       |
| toilet               | Toilet              |       |
| sink                 | Sink                |       |
| faucet               | KitchenFaucet       |       |
| sculpture            | Sculpture           |       |
| clock                | Clock               |       |
| cushion              | Cushion             |       |
| pouf                 | Pouf                |       |
| stool                | Stool               |       |
| recliner             | Recliner            |       |
| basket               | Basket              |       |

---

## Subcategories
The single source for all valid subcategory names. Add here **and** add a matching `Prefix Code` or `Keyword Map` entry.
`ingest_asset.py` validates output against this and derives the EFU `Mood` path from it.

| Subcategory             | Group                |
|-------------------------|----------------------|
| Bed                     | Furniture/Bed        |
| BunkBed                 | Furniture/Bed        |
| Daybed                  | Furniture/Bed        |
| Futon                   | Furniture/Bed        |
| Carpet                  | Furniture/Carpet     |
| Curtain                 | Furniture/Curtain    |
| CurtainBlind            | Furniture/Curtain    |
| RoomDivider             | Furniture/Curtain    |

| Parasol                 | Furniture/Parasol    |
| Armchair                | Furniture/Seating    |
| ArmchairOutdoor         | Furniture/Seating    |
| Barstool                | Furniture/Seating    |
| BarstoolOutdoor         | Furniture/Seating    |
| Bench                   | Furniture/Seating    |
| BenchOutdoor            | Furniture/Seating    |
| Chair                   | Furniture/Seating    |
| ChairOutdoor            | Furniture/Seating    |
| DiningChair             | Furniture/Seating    |
| Divan                   | Furniture/Seating    |
| HangingChair            | Furniture/Seating    |
| KidsChair               | Furniture/Seating    |
| LoungeChair             | Furniture/Seating    |
| Lounger                 | Furniture/Seating    |
| MassageChair            | Furniture/Seating    |
| OfficeChair             | Furniture/Seating    |
| Ottoman                 | Furniture/Seating    |
| Pouf                    | Furniture/Seating    |
| RattanChair             | Furniture/Seating    |
| Recliner                | Furniture/Seating    |
| RecliningChair          | Furniture/Seating    |
| SideChair               | Furniture/Seating    |
| Stool                   | Furniture/Seating    |
| SunLounger              | Furniture/Seating    |
| Loveseat                | Furniture/Sofa       |
| OfficeSofa              | Furniture/Sofa       |
| SectionalSofa           | Furniture/Sofa       |
| Sofa                    | Furniture/Sofa       |
| SofaOutdoor             | Furniture/Sofa       |
| BathroomCabinet         | Furniture/Storage    |
| Bookcase                | Furniture/Storage    |
| Cabinet                 | Furniture/Storage    |
| CabinetSet              | Furniture/Storage    |
| ClosetDecor             | Furniture/Storage    |
| Credenza                | Furniture/Storage    |
| DisplayCabinet          | Furniture/Storage    |
| DrawerChest             | Furniture/Storage    |
| Dresser                 | Furniture/Storage    |
| EntertainmentCenter     | Furniture/Storage    |
| OfficeStorage           | Furniture/Storage    |
| ShelvingUnit            | Furniture/Storage    |
| Sideboard               | Furniture/Storage    |
| Storage                 | Furniture/Storage    |
| TVStand                 | Furniture/Storage    |
| TvCabinet               | Furniture/Storage    |
| Wardrobe                | Furniture/Storage    |
| BarTable                | Furniture/Table      |
| BedsideTable            | Furniture/Table      |
| Billiard                | Furniture/Table      |
| CoffeeTable             | Furniture/Table      |
| CoffeeTableSet          | Furniture/Table      |
| ConsoleTable            | Furniture/Table      |
| Desk                    | Furniture/Table      |
| DiningSet               | Furniture/Table      |
| DiningTable             | Furniture/Table      |
| Nightstand              | Furniture/Table      |
| OfficeTable             | Furniture/Table      |
| SideTable               | Furniture/Table      |
| Table                   | Furniture/Table      |
| TableCenterpiece        | Furniture/Table      |
| TableOutdoor            | Furniture/Table      |
| TableSet                | Furniture/Table      |
| AssemblyEquipment       | Building             |
| Canopy                  | Building             |
| Ceiling                 | Building             |
| Door                    | Building             |
| Facade                  | Building             |
| Fence                   | Building             |
| FloorElement            | Building             |
| Gate                    | Building             |
| Ironmongery             | Building             |
| Louvre                  | Building             |
| MEP                     | Building             |
| Profile                 | Building             |
| Railing                 | Building             |
| Roof                    | Building             |
| Screen                  | Building             |
| Spandrel                | Building             |
| Wall                    | Building             |
| Window                  | Building             |
| ArchitecturalLight      | Fixture/Lighting     |
| CeilingLight            | Fixture/Lighting     |
| Chandelier              | Fixture/Lighting     |
| DeskLamp                | Fixture/Lighting     |
| FillLight               | Fixture/Lighting     |
| FloorLamp               | Fixture/Lighting     |
| Lantern                 | Fixture/Lighting     |
| Pendant                 | Fixture/Lighting     |
| PendantBranched         | Fixture/Lighting     |
| PendantCaged            | Fixture/Lighting     |
| PendantCrystal          | Fixture/Lighting     |
| PendantCylinder         | Fixture/Lighting     |
| PendantDrum             | Fixture/Lighting     |
| PendantGlobe            | Fixture/Lighting     |
| PendantIrregular        | Fixture/Lighting     |
| PendantLight            | Fixture/Lighting     |
| PendantLinear           | Fixture/Lighting     |
| PendantOrb              | Fixture/Lighting     |
| PendantRattan           | Fixture/Lighting     |
| PendantRectangular      | Fixture/Lighting     |
| PendantSet              | Fixture/Lighting     |
| PendantShaded           | Fixture/Lighting     |
| PendantSpiral           | Fixture/Lighting     |
| PendantStar             | Fixture/Lighting     |
| PendantTiered           | Fixture/Lighting     |
| PendantWaterfall        | Fixture/Lighting     |
| ReadingLamp             | Fixture/Lighting     |
| SkyLight                | Fixture/Lighting     |
| SpotlightAccent         | Fixture/Lighting     |
| StreetLight             | Fixture/Lighting     |
| StripLight              | Fixture/Lighting     |
| TableLamp               | Fixture/Lighting     |
| TroughLight             | Fixture/Lighting     |
| WallLamp                | Fixture/Lighting     |
| WallLight               | Fixture/Lighting     |
| Appliance               | Fixture              |
| BathroomAppliance       | Fixture              |
| BathroomFabric          | Fixture              |
| BathroomFixture         | Fixture              |
| BathroomPlumbing        | Fixture              |
| Bathtub                 | Fixture              |
| KitchenAppliance        | Fixture              |
| KitchenFabric           | Fixture              |
| KitchenFaucet           | Fixture              |
| KitchenFixture          | Fixture              |
| KitchenPlumbing         | Fixture              |
| KitchenSink             | Fixture              |
| OfficeAppliance         | Fixture              |
| RainShower              | Fixture              |
| ShowerHead              | Fixture              |
| ShowerMixer             | Fixture              |
| Sink                    | Fixture              |
| Toilet                  | Fixture              |
| Art                     | Object/Decor         |
| Basket                  | Object/Decor         |
| Book                    | Object/Tableware     |
| BookStack               | Object/Tableware     |
| Bowl                    | Object/Tableware     |
| Candle                  | Object/Decor         |
| Clock                   | Object/Decor         |
| Cookware                | Object/Tableware     |
| Cushion                 | Object/Decor         |
| DecorDisplay            | Object/Decor         |
| DigitalDecor            | Object/Decor         |
| DiningFood              | Object/Tableware     |
| DiningTableware         | Object/Tableware     |
| DisplayTableware        | Object/Tableware     |
| DrinksSet               | Object/Tableware     |
| DrinksTray              | Object/Tableware     |
| FloorPlanter            | Object/Plant         |
| FoodCart                | Object/Tableware     |
| FoodDisplay             | Object/Tableware     |
| FoodDrinks              | Object/Tableware     |
| FoodTray                | Object/Tableware     |
| Frame                   | Object/Decor         |
| FruitBowl               | Object/Tableware     |
| GreenWall               | Object/Plant         |
| Hobby                   | Object/Other         |
| Mirror                  | Object/Decor         |
| MusicDecor              | Object/Decor         |
| OfficeDecor             | Object/Decor         |
| PlanterBox              | Object/Plant         |
| PottedPlantSet          | Object/Plant         |
| PottedPlantTable        | Object/Plant         |
| Sculpture               | Object/Decor         |
| ServingPlatter          | Object/Tableware     |
| ShelvingDecor           | Object/Decor         |
| Tableware               | Object/Tableware     |
| Toy                     | Object/Other         |
| Tray                    | Object/Tableware     |
| Vase                    | Object/Decor         |
| WallDecor               | Object/Decor         |
| WineRelated             | Object/Tableware     |
| AquaticPlant            | Vegetation           |
| BambooTree              | Vegetation           |
| Cactus                  | Vegetation           |
| ConiferTree             | Vegetation           |
| CreeperPlant            | Vegetation           |
| CropPlant               | Vegetation           |
| DryPlant                | Vegetation           |
| FlowerGrass             | Vegetation           |
| FlowerPlant             | Vegetation           |
| FlowerShrub             | Vegetation           |
| FlowerTree              | Vegetation           |
| Gravel                  | Vegetation           |
| GreenWallForest         | Vegetation           |
| Groundcover             | Vegetation           |
| Hedge                   | Vegetation           |
| LargeTree               | Vegetation           |
| PalmTree                | Vegetation           |
| Plant                   | Vegetation           |
| Rock                    | Vegetation           |
| Shrub                   | Vegetation           |
| SmallTree               | Vegetation           |
| Succulent               | Vegetation           |
| Tree                    | Vegetation           |
| TreeStump               | Vegetation           |
| WildGrass               | Vegetation           |
| WildPlant               | Vegetation           |
| WinterTree              | Vegetation           |

---

## Usage Locations
Allowed values for the `People` (Usage Location) column.

| Location     |
|--------------|
| Bathroom     |
| Bedroom      |
| Balcony      |
| Commercial   |
| Dining Room  |
| Entryway     |
| Garden       |
| Garage       |
| Gym          |
| Hallway      |
| Hotel        |
| Kids Room    |
| Kitchen      |
| Library      |
| Living Room  |
| Lobby        |
| Office       |
| Outdoor      |
| Patio        |
| Restaurant   |
| Spa          |
| Study        |
| Terrace      |

---

## Ignore Folders
Folder names skipped during vendor path inference (case-insensitive).

| Folder Name            |
|------------------------|
| rar_without_zip        |
| _isolate_missing_pairs |
| tmp                    |
| temp                   |
| archive                |
| unzipped               |
| images                 |
| photos                 |
| misc                   |
| downloads              |
| 3d                     |


*End of document.*
