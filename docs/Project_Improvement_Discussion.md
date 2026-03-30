# Project Improvement Discussion

This document tracks the discussion and design for new features and workflow improvements in the RR_Repo ecosystem.

## User Inquiries (2026-03-27)

### 1. Project Overview and Status
*   **Question:** How to have an overview of projects and their status (e.g., outstanding issues for KIL112)?
*   **Decision:** **Centralized Markdown Checklists (Option C).** The user prefers a master Markdown file because it is the simplest to edit and doesn't require complex terminal commands or web interfaces to update. It aligns perfectly with the "Zero-Lock-In" philosophy. We will use a central `Active_Projects.md` (or similar) combined with project-specific `CHANGELOG.md` files.

### 2. Asset Categorization and Statistics
*   **Question:** What is the category list of 3D assets, and how many in each category?
*   **Initial Thought:** The `_index.csv` (managed by `sync_assets.py`) should be the source of truth. A simple Python script can aggregate counts by the `Category` field in the filename/metadata.

### 3. Asset Discovery and Reuse
*   **Question:** How to find a chair for a living room, preferring one used before in other projects?
*   **Decision:** *Scrapped.* The user decided to abandon this specific tracking requirement for now.

### 4. Client Instruction Tracking
*   **Question:** How to keep track of instructions from Email, WhatsApp, etc., without missing anything?
*   **Decision:** **The Inbox Pattern.** A centralized `inbox.md` file in the root of the Repo. The user will paste raw text (WhatsApp, emails) into this file. Unorganized files or screenshots will go to `D:/Dump`. When requested, the AI will process `inbox.md` to extract actionable tasks and organize them into the appropriate project trackers.

### 5. Quotation Management
*   **Question:** How to track quotations (status, details)? Should they live in GH or F: drive?
*   **Decision:** **Local Source (E: Drive), PDF Output.** Markdown source files for quotations will live in `RR_Repo/quotes/` for versioning. Status (Accepted/Rejected) and metadata will be tracked in the central `Active_Projects.md` hub. Delivered PDFs will be stored in the project's `01_Brief` or `03_Shared` folder on the F: drive.

### 6. Waveapps Integration
*   **Question:** Better way to integrate Waveapps with storage/workflow (access invoices/payments from NAS/Cloud, link to projects)?
*   **Decision:** **The Metadata Link (Option A).** Keep it simple. Add an `Invoice_URL` and `Payment_Status` column to the `Active_Projects.md` dashboard. When an invoice is created, paste the Waveapps shareable link and the local path to the downloaded PDF into the markdown hub. This acts as a manual but highly effective bridge.

### 7. Workflow Visualization
*   **Question:** Visual diagram of storage architecture, 3D workflows (rendering, animation)?
*   **Initial Thought:** Use **Mermaid.js** diagrams embedded in `docs/Architecture_Maps.md`. This keeps them "Zero-Lock-In" and easily editable in VS Code.

---

## Discussion Log
*   **2026-03-27:** User initiated the discussion with 7 key questions. Documentation created.
