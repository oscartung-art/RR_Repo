---
title: VS Code Setup Guide for RR_Repo
date: 2026-03-29
type: Process Guide
tags: [vscode, setup, google-drive, python, environment]
status: Active
---

# VS Code Setup Guide for RR_Repo

This guide provides step-by-step instructions for setting up the `RR_Repo` workspace in Visual Studio Code. The repo lives on Google Drive and is automatically mirrored to `D:\GoogleDrive\RR_Repo\` via Google Drive for Desktop — no Git or cloning required.

---

## 1. Prerequisites

Before you begin, ensure you have the following installed:

### 1.1 Google Drive for Desktop

The repo syncs automatically via Google Drive. Download and install Google Drive for Desktop [1] and sign in with `oscartung@real-hk.com`. Once synced, the repo will be available at `D:\GoogleDrive\RR_Repo\`.

### 1.2 Python 3.9+

Python is the primary language for the scripts in this repository. Download and install Python from the official website [2]. Ensure you select "Add Python to PATH" during installation.

### 1.3 Visual Studio Code

VS Code is the recommended IDE for this project. Download and install it from the official website [3].

---

## 2. Opening the Repository

No cloning is required. The repo is already on your machine via Google Drive.

1. **Open VS Code.**
2. **Open the `RR_Repo` folder:**
   - Go to `File > Open Folder...` (or `Ctrl+K Ctrl+O`).
   - Navigate to `D:\GoogleDrive\RR_Repo` and click `Select Folder`.

---

## 3. Python Environment Setup

1. **Install Recommended Extensions:**
   VS Code will likely recommend the "Python" extension by Microsoft. Click `Install` if prompted. If not, go to the Extensions view (`Ctrl+Shift+X`) and install `Python` and `Pylance`.

2. **Select the Python Interpreter:**
   - Open the Command Palette (`Ctrl+Shift+P`).
   - Type `Python: Select Interpreter` and select it.
   - Choose your installed Python version (e.g., `Python 3.11.0 64-bit`).

3. **Create a Virtual Environment (Recommended):**
   - Open the Integrated Terminal in VS Code (`` Ctrl+` ``).
   - From the repo root, create a virtual environment:
     ```bash
     python -m venv .venv
     ```
   - Activate it:
     ```bash
     .venv\Scripts\activate
     ```

4. **Install Dependencies:**
   With the virtual environment activated:
   ```bash
   pip install -r requirements.txt
   ```

---

## 4. Running Scripts

1. **Open the script file** in VS Code (e.g., `tools/sync_assets.py`).
2. **Ensure your virtual environment is activated** in the terminal.
3. **Run the script** using the green Run button, or in the terminal:
   ```bash
   python tools/your_script_name.py
   ```

---

## 5. Managing Knowledge Files

The knowledge base lives in Markdown files under `docs/`. You can:

- **Open and edit** `.md` files directly in VS Code.
- Use **Markdown Preview** (`Ctrl+Shift+V`) to see rendered output.
- Use **Global Search** (`Ctrl+Shift+F`) to find anything across all docs and scripts instantly.

---

## 6. Keeping Your Workspace Up-to-Date

Because the repo syncs via Google Drive, there is no `git pull` required. Simply:

1. Check the Google Drive tray icon to confirm sync is complete.
2. If Gemini CLI has been running, tell it: *"Re-read `gemini.md`."* to refresh its context.

---

## References

[1]: [Google Drive for Desktop](https://www.google.com/drive/download/)
[2]: [Python.org](https://www.python.org/downloads/)
[3]: [Visual Studio Code](https://code.visualstudio.com/)
