# Implementation Plan: `generate_3d_vertex.py` (Zero-Lock-In AI Generator)

## 1. Background & Motivation
The user prefers to use the **Google Cloud Vertex AI** ecosystem (specifically, new 3D generation capabilities) rather than subscribing to third-party services like Meshy or Tripo. This plan outlines the creation of a Python script that integrates directly with Vertex AI (via the modern `google-genai` SDK) to generate a 3D model from the cropped WhatsApp image of the fountain.

## 2. Scope & Impact
*   **Target:** A standalone tool in `tools/generate_3d_vertex.py`.
*   **Impact:** Empowers the "Studio Brain" to generate its own 3D assets on-demand. The user only pays per API call, satisfying the "Zero-Lock-In" and avoiding monthly software fees.
*   **Dependencies:**
    *   Requires a Google Cloud Project with the Vertex AI API enabled.
    *   Requires the `google-genai` Python SDK.
    *   Requires valid Google Cloud credentials (`gcloud auth application-default login`).

## 3. Proposed Solution
We will write a robust Python script that:
1.  Takes the path of a 2D image (the fountain) as an argument.
2.  Uses the `google-genai` client to send the image to a Vertex AI 3D model (e.g., `gemini-3-3d-preview` or an equivalent Model Garden endpoint).
3.  Requests the output in `.glb` format.
4.  Saves the resulting 3D file into the `G:\` Asset Mass Drive, ready to be picked up by `sync_assets.py`.

## 4. Implementation Plan

### Step 4.1: Environment Setup
*   Instruct the user to install the SDK: `pip install google-genai pillow`.
*   Instruct the user to authenticate with GCP (out of scope for the script itself, but necessary).

### Step 4.2: Draft `generate_3d_vertex.py`
The script will include:
*   **Arguments:** `--image` (path to input), `--output` (path to save `.glb`), `--project` (GCP Project ID).
*   **Client Initialization:** Setup the `genai.Client` for Vertex AI.
*   **API Call:** Send the image and prompt to the model.
*   **File Save:** Handle the binary `.glb` stream and write it to disk.

### Step 4.3: Integration with Pipeline
Once the `.glb` is saved (e.g., `G:\Furniture_VertexAI_GlassFountain_001.glb`), the user can run the existing `sync_assets.py` to index it.

## 5. Verification
*   We will create a TDD mock test in `tests/test_generate_3d.py` to ensure the argument parsing and file saving logic works before attempting a real API call (which costs money).

## 6. Alternatives Considered
*   **Procedural Generation (MaxScript/Python):** Highly accurate but lacks the visual nuance of AI textures. Rejected because the user specifically requested to try the Google ecosystem AI (Option 2).
*   **Third-Party APIs (Tripo/Meshy):** Faster setup, but violates the user's preference for Google ecosystem / pay-as-you-go infrastructure.
