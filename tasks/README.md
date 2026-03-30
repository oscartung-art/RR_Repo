# Three-Agent Handoff Protocol

This `tasks/` folder is the designated landing zone for cross-agent communication within the Real Rendering environment.

## The Workflow

Gemini Web (browser) is used for discussion and planning. When an actionable plan is reached that requires local file execution, Gemini Web generates a `.md` file following the `TASK_FORMAT.md` template and saves it in this folder. Manus or Gemini CLI then reads the pending task, performs the necessary file edits or script executions, and updates the task status from `pending` to `done`.

## File Naming Convention

All task files must follow this format: `YYYY-MM-DD_Task_Name.md`

Example: `2026-03-28_Create_Shared_Config.md`

## Agent Roles

| Agent | Role | Capability |
| :--- | :--- | :--- |
| **Gemini Web** | Planner & Architect | Generates task files, cannot execute locally |
| **Gemini CLI** | Local Executor (VS Code) | Reads and executes tasks on local machine |
| **Manus AI** | Autonomous Executor | Reads and executes tasks, can access Google Drive mount. Uses `gemini.md` as brain. |

## Status Values

| Status | Meaning |
| :--- | :--- |
| `pending` | Task written by Gemini Web, waiting for execution |
| `in-progress` | Executor has picked it up and is working |
| `done` | Task completed successfully |
