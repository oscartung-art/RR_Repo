---
title: AI Terminal Workflow Guide
id: ai-terminal-workflow-guide
date: 2026-03-27
type: Process Guide
tags: [workflow, gemini, cli, terminal, context]
status: Active
---

# 🚀 AI Terminal Workflow Guide

This guide outlines the core technique for using the Gemini CLI within your terminal environment, consolidating the philosophies of local, context-driven AI workflows.

## 1. The Core Philosophy: Terminal AI + Persistent Context

When using AI in a browser window, you encounter severe limitations: context loss over long conversations, chat clutter, and constant copy/pasting.

Instead of bringing your work *to* the AI, bring the AI *to* your work. Because tools like the Gemini CLI run directly in your terminal, they can read and write files on your hard drive natively. The secret to this efficiency is **Persistent Context** through Context Files.

## 2. Environment Setup

### 2.1 VS Code Configuration
Use VS Code as your command center:
*   **Integrated Terminal**: Open your terminal in VS Code (`Ctrl + \``).
*   **Split Panes**: Use split terminals (`Ctrl + Shift + 5`) to run multiple tasks simultaneously.
*   **File Explorer**: Keep your project folder open on the left to see the AI creating and modifying files in real-time.

### 2.2 Tool Installation
Ensure you have the Gemini CLI installed globally:
```bash
npm install -g @google/gemini-cli
```

## 3. The Context File Strategy (`gemini.md`)

The secret to efficiency is the context file. Instead of re-explaining your project to the AI every time, you use Markdown files that act as the project's "memory."

1.  **Initialization:** Navigate to your project folder and run `/init` inside the Gemini CLI. This creates a `gemini.md` file.
2.  **Updating:** When you change a fundamental rule or tool, instruct Gemini: *"Update `gemini.md` to reflect that we are using Python instead of Node.js now."* The next time you open the CLI, it remembers the new rule automatically.
3.  **Cross-Session Memory:** You can close your terminal completely. When you return days later, Gemini automatically loads `gemini.md` in the background. You do not have to re-explain the project.

## 4. Daily Integrated Workflow

### Essential Commands
*   **Start Gemini:** `gemini`
*   **Exit Gemini:** `exit` or `Ctrl+C`
*   **Show Tools:** `/tools`
*   **Show Help:** `/help`

### File Operations
Gemini can read and write files directly. This is the most efficient way to work.
*   **Reading:** *"Read `docs/Naming_Convention.md` to check my rules."*
*   **Creating/Editing:** *"Create a new script `tools/test_connection.py` that checks the API."*

### Knowledge Base Workflow (SOP)
Follow these steps when using Gemini to manage your documentation:
1.  **Reference:** Tell Gemini which file to look at (e.g., *"Read `docs/AI_System_Prompt.md`."*).
2.  **Instruct:** Provide the update (e.g., *"Update the guide to include the new `acp` alias."*).
3.  **Validate:** Open the file in the VS Code editor to see the changes in real-time.

## 5. Headless Mode & Piping Commands

You can use headless mode to execute one-shot commands without entering the chat interface.

### The `-p` Flag (Prompt)
Execute a string and immediately exit:
```bash
gemini -p "Read the content of a.txt, analyze the data, and generate a summary report. Save the output to reports/summary_v1.md"
```

### Terminal Piping
Feed text output directly into Gemini:
```powershell
Get-Content a.txt | gemini -p "Summarize this data and save it to ./reports/summary.md"
```

Use headless mode for automation, speed, and command chaining (e.g., `git diff | gemini -p "Write a commit message for these changes"`).