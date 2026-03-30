---
id: 2026-03-29_Establish_Action_Log_System
title: Establish Markdown Action Log System and SOPs
status: done
---

Please execute the following setup and memorize these SOPs for our workspace located at D:\GoogleDrive\RR_Repo\.

1.  **Create the Action Log:**
    Create a new file at `D:\GoogleDrive\RR_Repo\docs\action_log.md`. Initialize it with this exact Markdown table:

    ```markdown
    # Action Log
    | #ID | Date       | Project | Description | Status    |
    | :-- | :--------- | :------ | :---------- | :-------- |
    ```

2.  **Update Naming Conventions:**
    Check the `docs/` folder for your existing naming conventions file. Add a new section for Action Log Status Tags. The only permitted statuses are: `Pending`, `In Progress`, `Blocked`, `Done`, `Cancelled`. If a naming conventions file doesn't exist, create `docs/naming_conventions.md` and add this rule.

3.  **Update Single Source of Truth:**
    Open `D:\GoogleDrive\RR_Repo\gemini.md` and add the following bullet point under the **Strategic Workflows** section:
    -   **Task Tracking:** Active tasks logged in `docs/action_log.md` using #ID for quick status updates.

4.  **Future SOP - Adding Entries:**
    When I ask you to log an update (e.g., "Hey for KIL112, client wants me to..."):
    -   Find the highest #ID in `action_log.md` and increment by 1.
    -   Format the current date (YYYY-MM-DD), extract the project code, and summarize the description.
    -   Append the new row using the default status `Pending`.

5.  **Future SOP - Updating Entries:**
    When I say "Update #1 to Done":
    -   Find the exact row matching the #ID in `action_log.md`.
    -   Replace the value in the Status column with the new valid tag.
    -   Save the file without breaking the table formatting.

6.  **Future SOP - Archiving Entries:**
    When I say "Archive Done Tasks":
    -   Move all rows marked `Done` or `Cancelled` from `action_log.md` to `D:\GoogleDrive\RR_Repo\docs\action_log_archive.md`.
    -   If the archive file doesn't exist, create it with the same table headers as the main log.
