# Common Terminal Commands (RR_Repo)

This guide stores the most frequent commands used to navigate and manage the Studio Brain.

## 1. Project Lookup (Quick Dashboard)
View a clean summary of any project directly in the terminal:
```bash
# General Usage
p PROJECT_CODE

# Example
p PLS
```

## 2. Project Management (Internal)
View the active "To-Do List" and project status:
```bash
gh issue list
```

## 2. Searching Information (Grep)
Find specific project details, client names, or SOPs within the knowledge base:
```bash
# Search for a project code across all documentation files
grep -r "PROJECT_CODE" docs/

# Search for project details in your project master index
grep -i "PROJECT_CODE" db/Project_Master_Index.csv

# Example:
# grep -r "KIL11285" docs/
```

## 3. Navigation
Show the current repository structure (useful for the AI):
```bash
ls -R
```

## 4. Asset Library
Search your indexed asset library (once `_index.csv` is populated):
```bash
grep -i "TEXTURE_NAME" G:/_index.csv
```
