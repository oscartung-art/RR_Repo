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

**Description:** Project Inspector. Displays detailed metadata and drive paths for a specific project.

**Usage:**
```
rr p [project_code]
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

