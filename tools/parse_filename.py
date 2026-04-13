import os
import sys
import json
import urllib.request
import google.auth
from google.auth.transport.requests import Request

def _get_vertex_auth_token():
    credentials, project_id = google.auth.default()
    if not credentials.valid:
        credentials.refresh(Request())
    return credentials.token, project_id

def parse_filename(filename_text):
    # Setup Vertex AI configurations
    token, project_id = _get_vertex_auth_token()
    project_id = os.environ.get("VERTEX_PROJECT_ID", project_id)
    location = os.environ.get("VERTEX_LOCATION", "us-central1")
    
    if not project_id:
         print("Error: Could not determine Google Cloud Project ID. Set VERTEX_PROJECT_ID environment variable.")
         sys.exit(1)

    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/gemini-2.0-flash:generateContent"

    # Strict prompt to ONLY return JSON
    prompt = f"""
You are a furniture and 3D asset metadata expert. 
Analyze this source filename: "{filename_text}"

Extract the Model Name (Author) and the Brand/Manufacturer (Writer).
Often, brands are well-known furniture companies (e.g., Minotti, Hansgrohe, Frigerio, Dedon, Rossin, BBItalia).
The rest of the text is the model/collection name.

Reply ONLY with a raw JSON object and no markdown formatting.
Example: {{"Author": "Vernis Blend", "Writer": "Hansgrohe"}}
"""

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.1, # Low temperature for more factual splitting
            "responseMimeType": "application/json"
        }
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            
            # Extract text response containing JSON
            text_content = response_data['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up potential markdown formatting just in case
            if text_content.startswith('```json'):
                text_content = text_content[7:-3]
            
            parsed_json = json.loads(text_content.strip())
            return parsed_json

    except urllib.error.HTTPError as e:
         print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
         return None
    except Exception as e:
         print(f"Error parsing response: {e}")
         return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/parse_filename.py <filename_text>")
        sys.exit(1)

    input_text = sys.argv[1]
    print(f"Analyzing: '{input_text}'...")
    
    result = parse_filename(input_text)
    if result:
        print("\n--- AI Extraction Result ---")
        print(f"Author (Model): {result.get('Author', '-')}")
        print(f"Writer (Brand): {result.get('Writer', '-')}")
