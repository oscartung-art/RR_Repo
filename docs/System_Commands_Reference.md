# System Commands Reference

This document serves as a centralized reference for all custom terminal commands used throughout the RR_Repo system. It is designed to be easily searchable and extensible, aligning with the project's text-based, zero-lock-in principles.

---

## Command Structure:

Each command entry follows this structure:

```
### `[COMMAND_NAME]`

**Description:** A concise explanation of what the command does.

**Usage:**
```
[command] [arguments]
```

**Example:**
```
[example_command]
```

**Notes:** Any additional important information or caveats.
```

---

## Available Commands:

### `p`

**Description:** Project Inspector. Displays detailed metadata and drive paths. Supports sub-views for deep inspection.

**Usage:**
```
rr p [project_code] [docs|contacts|links|full]
```

### `open`

**Description:** Folder Opener. Instantly opens the project's F: drive directory in Windows File Explorer.

**Usage:**
```
rr open [project_code]
```

### `c`

**Description:** Clipboard Tool. Instantly copies a specific field from a project file directly to your Windows clipboard.

**Usage:**
```
rr c [project_code] [category] [field]
```

**Example:**
```
rr c PLS links client_drive
```

### `dash`

**Description:** Project Dashboard. Displays a categorized summary of all projects (Leads, Active, Completed).

**Usage:**
```
rr dash
```

### `crm`

**Description:** CRM Database Viewer. Displays a formatted table of all contacts. Add a search term to filter results.

**Usage:**
```
rr crm [optional_search_term]
```

### `help`

**Description:** Help Menu. Displays this list of commands or detailed information about a specific command.

**Usage:**
```
rr help [command]
```

