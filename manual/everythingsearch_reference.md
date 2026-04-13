# Everything Search Reference (2026)

Concise, practical reference for Everything (voidtools) covering search syntax, advanced features, CLI, customization, shortcuts, and troubleshooting.

---

## Recursive Crawl Results (depth=3)

### Everything 1.5 Alpha (forum index)
- URL: https://www.voidtools.com/forum/viewforum.php?f=12
- Snapshot: forum index for "Everything 1.5 Alpha" — lists many topic starter threads by `void` (developer) and others. Useful threads discovered: `.metadata.efu Specification`, `Search Functions`, `Command-line Options`, `INI Settings`, `Keyboard Shortcuts`, `File Lists`, `Indexing`, and many bug/feature report threads. This index is a good entry point to follow developer posts and topic first-posts.

### Support — Searching (intro)
- URL: https://www.voidtools.com/support/everything/searching
- Snapshot: primary search syntax documentation — operators (AND/OR/NOT/quotes), wildcards (`*`, `?`), modifiers (`case:`, `regex:`, `path:`), functions (`size:`, `dm:`, `ext:`, `dupe:`), date/size syntax, examples, and notes that content/ID3/image searches are slow (not indexed).

### Support — Keyboard Shortcuts (intro)
- URL: https://www.voidtools.com/support/everything/keyboard_shortcuts
- Snapshot: default shortcuts grouped by context (search edit, result list, global, hotkeys). Highlights: `Ctrl+Space` complete (history), `F3`/`Ctrl+F` focus search, `F5` reload, `Ctrl+R` toggle regex, `Ctrl+S` export results, `Ctrl+Shift+C` copy full path.

### Forum — Developer profile (limited)
- URL: https://www.voidtools.com/forum/memberlist.php?mode=viewprofile&u=809
- Snapshot: profile pages require login to view full profile content; public metadata shows the user `void` (developer) as the main poster of alpha announcements and reference threads.

Notes:
- I followed the explicit voidtools.com/forum and support links found in the original thread first post. The forum index exposes many related threads that can be fetched individually — if you want, I can now fetch the first-post of each of the top N threads (e.g., `.metadata.efu Specification`, `Search Functions`, `Command-line Options`) to include their first-post text and links. Specify N or confirm fetch all visible developer threads.

---

## Quick Syntax Cheat-sheet

- Basic: type partial filenames. Limit by drive `d:` or folder `d:\downloads\`.
- Exact phrase: "text"
- Operators: space = AND, `|` = OR, `!` = NOT
- Wildcards: `*` (0+ chars), `?` (1 char)
- Modifiers: `case:`, `nocase:`, `diacritics:`, `nodiacritics:`, `file:`, `folder:`, `path:`, `nopath:`, `regex:`
- Common functions: `size:`, `dm:` (date modified), `dc:` (date created), `da:` (date accessed), `ext:`, `parent:`, `filelist:`, `dupe:`, `content:` (slow)
- Size syntax: `size[kb|mb|gb]` and constants: `tiny, small, medium, large, huge, gigantic`
- Date examples: `dm:today`, `dm:thisweek`, `dm:2026-01-01..2026-04-09`

---

## Advanced

- Advanced Search dialog (Search → Advanced Search) for building complex queries.
- Filters = named, reusable searches; macros can map `name:` to filter.
- Bookmarks save search+filter+sort+index.
- Regex: `regex:` prefix; regex disables normal operators/wildcards.

---

## CLI (es.exe)

- Usage: `es.exe [options] [search text]` (Everything must be running)
- Useful options: `-r`/`-regex`, `-i`/`-case`, `-w`/`-ww`(whole word), `-p`/`-match-path`, `-n <num>`, `-s` (sort), `-csv`/`-efu`/`-txt`, `-export-csv out.csv`
- Examples:
  - `es.exe *.mp3 -export-efu mp3.efu`
  - `es.exe -sort size -n 10` (top 10 largest)

---

## Options & Indexing

- Options (Tools → Options) cover General, UI, Home, Search, Results, View, Context Menu, Fonts, Keyboard, History, Indexes (NTFS/ReFS/Folders/File Lists/Exclude), ETP/HTTP servers.
- Index settings: database location, index extra columns (size, dates, attributes) for faster searches/sorts; Force Rebuild available.
- Exclude by folder, wildcard, or `regex:` filters.

---

## Customization

- Everything.ini for advanced tweaks (window title format, date/time formats, fonts, colors, status bar format, HTTP/ETP messages).
- External file manager configured in Context Menu → Open Path with `$exec()` syntax.

---

## Keyboard Shortcuts (high-priority)

- Search edit: `Ctrl+A` select all, `Ctrl+Space` complete (history enabled), `Enter` focus results
- Result list: `F2` rename, `Delete` recycle, `Shift+Delete` permanent, `Enter` open, `Ctrl+Shift+C` copy full path
- Global: `F3`/`Ctrl+F` focus search, `F5` reload, `Ctrl+R` toggle regex, `Ctrl+S` export results, `Alt+Home` go home

---

## Troubleshooting

- If search misses files: disable Match Case/Whole Word/Path/Diacritics/Regex; ensure filter = Everything; enable non-NTFS volumes in Options → Folders; Force Rebuild.
- Duplicates: remove NTFS volumes from folder indexes (NTFS auto-indexing causes duplicates).
- Settings not saved: enable Store settings and data in `%APPDATA%\Everything`.
- HTTP server: change port if port 80 conflict.
- Debug: `Ctrl+`` toggles debug console.

---

## Links

- Main support: https://www.voidtools.com/support/everything/
- Search syntax: https://www.voidtools.com/support/everything/searching
- Command line: https://www.voidtools.com/support/everything/command_line_options
- Options reference: https://www.voidtools.com/support/everything/options
- Keyboard shortcuts: https://www.voidtools.com/support/everything/keyboard_shortcuts
- Troubleshooting: https://www.voidtools.com/support/everything/troubleshooting

*Generated: 2026-04-09*

---

## Crawled Forum: "Properties" (Everything 1.5 Alpha) — first post

Source: https://www.voidtools.com/forum/viewtopic.php?f=12&t=9788

Summary of first post (author: void, Sat Mar 13, 2021):
- Introduces "Properties" in Everything 1.5: file metadata exposed as searchable/sortable/indexed properties (Length, Author, Tags, Size on Disk, Filename length, Dimensions, etc.).
- Demonstrates adding and showing property columns, searching and sorting by property, finding property duplicates, and using fast sort for instant property sorts.
- Explains property gathering priority: User values, `.metadata.efu`, alternate data streams (wchar/ansi/utf8), Opus meta, XYplorer tag.dat, Windows Property System, Summary Information, Everything Properties.
- Notes UI steps for adding properties to index, configuring include-only folders/file types, fast sort, and forcing reindexing.
- Provides examples and code snippets for Desktop.ini property setting and CSV user-values for `property_user_values`.

Links discovered in first post (followed where resolvable):
- Developer profile: https://www.voidtools.com/forum/memberlist.php?mode=viewprofile&u=809
- Images referenced (inline): https://www.voidtools.com/view.property2.png, https://www.voidtools.com/length.column.png, https://www.voidtools.com/search.for.length2.png, https://www.voidtools.com/length.sort.png, https://www.voidtools.com/select.property.png, https://www.voidtools.com/awesome.folder.png
- Support pages (referenced topics / further reading):
  - `.metadata.efu` (sidecar docs) — referenced; see https://www.voidtools.com/support/everything/ (and specific support pages linked in the manual)
  - Alternate data stream property handlers (wchar/ansi/utf8) — referenced in post (support pages exist under the Everything support index)
  - Opus Meta Information, XYplorer tag.dat, Summary Information — referenced as property sources (see support index links)
- Forum navigation links: Return to "Everything 1.5 Alpha" forum: https://www.voidtools.com/forum/viewforum.php?f=12

Notes on recursive crawling:
- This crawl captured the first post text and the explicit links embedded in it. The post mainly references support pages (already crawled earlier) and images; it did not include many other forum thread `viewtopic.php` links in the first post body.
- I can now follow each referenced support page or forum link and fetch that page's first post (or full page) recursively. Current plan uses depth=3 if you want full recursion — tell me if you want a larger depth or only forum threads (not support docs/images).

---

---

## Top 3 Developer Threads — First-Post Summaries

### 1) `.metadata.efu Specification`
- URL: https://www.voidtools.com/forum/viewtopic.php?t=16866
- Summary: Introduces `.metadata.efu` sidecar CSV files that provide property values for files/folders (Filename, Rating, Tags, CRCs, media properties, etc.). Files are CSV-based, UTF-8 encoded, and filenames are relative to the `.metadata.efu` file. Everything checks `.metadata.efu` files up the directory hierarchy until a non-null value is found; indexed `.metadata.efu` makes lookups instant. Notes on usage: include `.metadata.efu` in index, use `is-metadata-efu-property:` to search for files with defined metadata properties, refresh properties with `F5` and `Ctrl+F5` for indexed properties. Developer Q&A clarifies priority, indexing, and format constraints (no full absolute paths; relative only).

### 2) `Search Functions`
- URL: https://www.voidtools.com/forum/viewtopic.php?t=10176
- Summary: Comprehensive list of search functions introduced for Everything 1.5 (property-based functions such as `width:`, `height:`, `audio-bitrate:`, `dupe:`, `content:`, `property-system:` and many more). Describes behavior, weights (fast indexed → slow content), examples for semicolon-separated lists, substitution syntax (`$property:`), and notes about slow content searches. The thread includes many developer posts adding and evolving functions across alpha releases — useful for discovering exact property names and examples.

### 3) `Command-line Options`
- URL: https://www.voidtools.com/forum/viewtopic.php?t=10479
- Summary: Exhaustive command-line reference for Everything/Everything64 and `es.exe` usage: install/uninstall flags, DB and index manipulation (`-reindex`, `-db`, `-add-folder`), searching flags (`-s`, `-regex`, `-case`, `-n`), export options (`-csv`, `-efu`, `-export-csv`), filelist/file-list-slot ops, and GUI/result manipulation flags (`-columns`, `-sort`, `-select`). Includes JSON/array syntaxes for complex options and examples for automation and service/install scenarios.

If you want these expanded with full first-post text or images captured as links, tell me which thread(s) to expand further.

---

## Detailed Reference (crawled pages)

### Overview (main support)
- Everything is a lightweight, fast filename search engine for Windows with a small DB and real-time updating.
- Downloadable offline help: Everything.chm or HTML bundle; see support index for related docs.

### Searching (syntax & features)
- Operators: space=AND, `|`=OR, `!`=NOT, parentheses for grouping, quotes for exact phrases.
- Wildcards: `*` and `?` (wildcards match the whole filename unless option changed).
- Modifiers: `case:`, `nocase:`, `diacritics:`, `nodiacritics:`, `file:`, `folder:`, `path:`, `nopath:`, `regex:` and `wfn:`/`nowfn:` variants.
- Functions: many `name:value` helpers (`size:`, `dm:`, `dc:`, `da:`, `ext:`, `parent:`, `filelist:`, `dupe:`, `content:`). Use function comparison operators (`>`, `<`, `start..end`).
- Content searching is slow (not indexed) — combine `content:` with file-type filters and prefer other indexed filters where possible.
- Regex mode overrides normal syntax; escape space and `|` with double quotes when using `regex:`.
- Useful examples included (drive-limited searches, date ranges, size filters, dupe searches).

### Command line (Everything.exe / es.exe)
- Two CLI families: `Everything.exe` options to start/control GUI/service and `es.exe` small CLI client for scripted queries (requires Everything running).
- Groups: installation flags, filelist/EFU manipulation, ETP/HTTP, searching, results, database, window, and multi-file renaming.
- Common flags: `-n <num>`, `-s <sort>`, `-csv`/`-efu`/`-txt` exports, `-export-csv`, `-regex`, `-case`/`-nocase`, `-filter`, `-parent`, `-search`/`-s`.
- Admin/install options exist (`-install`, `-install-service`, `-install-options`, `-install-efu-association`); many require elevated privileges.
- Notes: use `-db` to operate on alternate DBs, `-reindex`/`-rebuild` to force rebuilds, and `/config_save` `/config_load` for config backups.

### Options & Indexing (key actionable items)
- General: control settings storage (`%APPDATA%\Everything`), run-as-admin, Everything Service, EFU association, URL protocol `es:`.
- UI/Home/Search: default match case/wholeword/path/diacritics/regex and Search-as-you-type toggle.
- Indexes: choose DB location, enable indexing of size/dates/attributes for faster searches/sorts, Force Rebuild button available.
- NTFS/USN: Everything uses USN Journal for NTFS volumes — enable per-volume monitoring; adjust USN max size/allocation if rebuilds fail.
- Folders & File Lists: include non-NTFS volumes via Folder indexes; File Lists (EFU) can be indexed and created/edited from UI or CLI.
- Exclude: use folder, wildcard or `regex:` filters to exclude files/folders from index.
- ETP/HTTP: embedded servers with auth, bind interfaces, ports, logging, and options to allow/deny downloads; useful for remote access.

### Keyboard Shortcuts (highlights)
- Search edit: `Ctrl+A`, `Ctrl+Space` (complete via history), `Enter` to focus results.
- Results: `F2` rename, `Delete`/`Shift+Delete`, `Ctrl+Shift+C` copy full path, `Enter` open, navigation keys and selection modifiers.
- Global: `F3`/`Ctrl+F` focus search, `F5` reload, `Ctrl+R` toggle regex, `Ctrl+S` export results, `Alt+Home` go home.
- Hotkeys: configurable to show/toggle new/search windows; require Everything running in background.

### Troubleshooting (practical steps)
- Missing results: disable Match Case/Whole Word/Path/Diacritics/Regex; ensure filter=`Everything`; include non-NTFS volumes under `Folders` and Force Rebuild if needed.
- Duplicates: remove NTFS volumes from Folder indexes (NTFS auto-indexing + explicit folder indexes both show duplicates).
- Settings not saved: enable `Store settings and data in %APPDATA%\Everything` or use `/config_save` to back up `Everything.ini`.
- Rebuilds & USN Journal: use Force Rebuild; to recreate USN Journal toggle USN logging off/on per volume in NTFS tab.
- HTTP/ETP server issues: change port if conflict (e.g., port 80); verify bind interfaces and credentials.
- Debug: toggle debug console with `Ctrl+` and check forum/support pages for specific error threads.

---
