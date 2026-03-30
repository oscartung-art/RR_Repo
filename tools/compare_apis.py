import os
import json
import time
import argparse
import requests
import google.auth
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google import genai
from google.genai import types

# Optional Vertex AI import (may fail if not installed, we'll handle gracefully)
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part as VertexPart
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False

# ---------------------------------------------------------------------------
# Setup & Auth
# ---------------------------------------------------------------------------
def setup_credentials():
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS not set.")
        exit(1)
        
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/cloud-platform"
    ]
    credentials, project_id = google.auth.default(scopes=scopes)
    credentials.refresh(Request())
    return credentials, project_id

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set.")
        exit(1)
    return genai.Client(api_key=api_key)

# ---------------------------------------------------------------------------
# API 1: Gemini 2.5 Flash (AI Studio)
# ---------------------------------------------------------------------------
def run_gemini_ai_studio(client, image_bytes, mime_type, prompt):
    print("  -> Running Gemini 2.5 Flash (AI Studio)...")
    start = time.time()
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(temperature=0.2)
        )
        elapsed = time.time() - start
        return response.text, elapsed
    except Exception as e:
        return f"Error: {e}", 0

# ---------------------------------------------------------------------------
# API 2: Vertex AI (Google Cloud)
# ---------------------------------------------------------------------------
def run_vertex_ai(project_id, image_bytes, mime_type, prompt):
    print("  -> Running Vertex AI Gemini...")
    if not VERTEX_AVAILABLE:
        return "Skipped: google-cloud-aiplatform package not installed. Run: pip install google-cloud-aiplatform", 0
        
    # Try multiple model versions in order of preference
    model_candidates = [
        "gemini-2.0-flash-001",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.0-pro-vision-001",
    ]
    
    start = time.time()
    for model_name in model_candidates:
        try:
            vertexai.init(project=project_id, location="us-central1")
            model = GenerativeModel(model_name)
            image_part = VertexPart.from_data(data=image_bytes, mime_type=mime_type)
            
            response = model.generate_content(
                [image_part, prompt],
                generation_config={"temperature": 0.2}
            )
            elapsed = time.time() - start
            return f"[Model: {model_name}]\n{response.text}", elapsed
        except Exception as e:
            err_str = str(e)
            if "404" in err_str or "not found" in err_str.lower() or "does not have access" in err_str.lower():
                print(f"     Model '{model_name}' not available, trying next...")
                continue
            else:
                return f"Error with {model_name}: {e}", 0
    
    return ("Skipped: No Vertex AI generative models are available on this project.\n"
            "Note: Projects created via Google AI Studio (gen-lang-client-*) typically\n"
            "do not have access to Vertex AI generative models. A standard GCP project\n"
            "with Vertex AI API enabled is required."), 0

# ---------------------------------------------------------------------------
# API 3: Google Cloud Vision API
# ---------------------------------------------------------------------------
def run_cloud_vision(credentials, image_bytes):
    print("  -> Running Google Cloud Vision API...")
    start = time.time()
    try:
        url = "https://vision.googleapis.com/v1/images:annotate"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
        
        import base64
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        
        payload = {
            "requests": [
                {
                    "image": {"content": encoded_image},
                    "features": [
                        {"type": "LABEL_DETECTION", "maxResults": 10},
                        {"type": "LOGO_DETECTION", "maxResults": 3},
                        {"type": "OBJECT_LOCALIZATION", "maxResults": 5}
                    ]
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if "error" in data:
            return f"API Error: {data['error']}", 0
            
        result = data.get("responses", [{}])[0]
        
        # Format output
        labels = [l.get("description") for l in result.get("labelAnnotations", [])]
        logos = [l.get("description") for l in result.get("logoAnnotations", [])]
        objects = [o.get("name") for o in result.get("localizedObjectAnnotations", [])]
        
        out = f"Labels: {', '.join(labels)}\n"
        out += f"Logos/Brands: {', '.join(logos) if logos else 'None detected'}\n"
        out += f"Objects: {', '.join(objects)}"
        
        elapsed = time.time() - start
        return out, elapsed
    except Exception as e:
        return f"Error: {e}", 0

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Compare Vision APIs")
    parser.add_argument("--folder", required=True, help="Folder name in Drive")
    parser.add_argument("--limit", type=int, default=3, help="Number of images to test")
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"API COMPARISON TEST: {args.folder}")
    print("=" * 60)
    
    credentials, project_id = setup_credentials()
    # Fallback to the known project ID if default doesn't provide one
    if not project_id:
        project_id = "gen-lang-client-0816223034"
        
    gemini_client = get_gemini_client()
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # 1. Find folder
    query = f"name = '{args.folder}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    res = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = res.get('files', [])
    if not items:
        print(f"Folder '{args.folder}' not found.")
        return
    folder_id = items[0]['id']
    
    # 2. Get images
    query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
    res = drive_service.files().list(q=query, fields="files(id, name, mimeType)", pageSize=args.limit).execute()
    images = res.get('files', [])
    
    if not images:
        print("No images found.")
        return
        
    prompt = """Analyze this image. Return a short summary including: Category, Subcategory, Brand, Material, and Style."""
    
    # 3. Test each image
    for img in images:
        print(f"\n\n--- Testing Image: {img['name']} ---")
        
        # Download
        url = f"https://www.googleapis.com/drive/v3/files/{img['id']}?alt=media"
        resp = requests.get(url, headers={"Authorization": f"Bearer {credentials.token}"})
        if resp.status_code != 200:
            print("Failed to download image.")
            continue
        image_bytes = resp.content
        
        # Run APIs
        res_gemini, t_gemini = run_gemini_ai_studio(gemini_client, image_bytes, img['mimeType'], prompt)
        res_vertex, t_vertex = run_vertex_ai(project_id, image_bytes, img['mimeType'], prompt)
        res_vision, t_vision = run_cloud_vision(credentials, image_bytes)
        
        # Print Results
        print("\n[1] Gemini 2.5 Flash (AI Studio) - {:.2f}s".format(t_gemini))
        print("-" * 40)
        print(res_gemini.strip())
        
        print("\n[2] Vertex AI (Gemini 1.5 Flash) - {:.2f}s".format(t_vertex))
        print("-" * 40)
        print(res_vertex.strip())
        
        print("\n[3] Google Cloud Vision API - {:.2f}s".format(t_vision))
        print("-" * 40)
        print(res_vision.strip())

if __name__ == "__main__":
    main()
