---
title: Quotation Generation Rules for Real-HK
date: 2026-03-25
type: Reference
tags: [naming, convention, files, folders, github, database]
status: Active
---


# Real-HK Quotation Generation Rules

## 1. Core Formatting & File Structure
- **Format:** All quotations MUST be generated as `.md` (Markdown) files.
- **Naming Convention:** `YYYY-MM-DD_Quotation_[ClientName].md`
- **Output:** The markdown should use clean tables for the pricing breakdown.

## 2. Standard Pricing & Items
- **Rendering:** Exterior rendering >20pcs = $18,000 HKD (Base unit)
- **Rendering:** Interior rendering >20pcs = $18,000 HKD (Base unit)
- **Animation:** 4K CG Animation >60s = $500 HKD per second
- **Animation (Box):** Digital Exp Zone animation >60s = $500 HKD per second
- **Modeling:** Clubhouse, G/F entrance & lobby, building exterior = $180,000 HKD

## 3. Financial Rules & Math
The agent must calculate the total and generate the payment terms based on the final calculated sum:
- **Deposit 1:** 30% invoiced upon confirmation of quotation.
- **Deposit 2:** 40% invoiced upon confirmation of camera angles.
- **Final:** 30% invoiced upon completion of the project.
- *Currency is strictly Hong Kong Dollars (HKD).*

## 4. Required Markdown Template Structure
When generating a quote, always use this structure:
1. Document Title (e.g., `# Quotation: Rendering + CG animation`)
2. `**Date of Quote:** [Insert Date] (valid 30 days)`
3. `## 1. Parties` (List The Client and The Consultant: Real Rendering, Oscar Tung)
4. `## 2. Deliverables` (Use a Markdown table with Item, Description, Unit Price)
5. `## 3. Terms` (List the 30/40/30 split calculated in HKD)