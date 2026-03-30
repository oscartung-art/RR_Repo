import os
import json
import argparse
import requests
import google.auth
from google.auth.transport.requests import Request

def setup_credentials():
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS not set.")
        exit(1)
        
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    credentials, _ = google.auth.default(scopes=scopes)
    credentials.refresh(Request())
    return credentials

def search(query, credentials, project_number, data_store_id):
    print(f"Searching for: '{query}'...")
    
    url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/global/collections/default_collection/dataStores/{data_store_id}/servingConfigs/default_search:search"
    
    payload = {
        "query": query,
        "pageSize": 5,
        "contentSearchSpec": {
            "snippetSpec": {"returnSnippet": True},
            "summarySpec": {
                "summaryResultCount": 3,
                "includeCitations": True
            }
        }
    }
    
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"Error: {response.text}")
        return
        
    data = response.json()
    
    # Print Summary if available
    summary = data.get("summary", {}).get("summaryText")
    if summary:
        print("\n--- AI Summary ---")
        print(summary)
        print("------------------\n")
        
    # Print Results
    results = data.get("results", [])
    if not results:
        print("No results found.")
        return
        
    print(f"Found {len(results)} top results:\n")
    for i, res in enumerate(results, 1):
        doc = res.get("document", {})
        struct_data = doc.get("structData", {})
        
        filename = struct_data.get("filename", "Unknown")
        tags = struct_data.get("tags", "")
        comment = struct_data.get("comment", "")
        
        print(f"{i}. File: {filename}")
        print(f"   Tags: {tags}")
        print(f"   Desc: {comment}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Search the Asset Database")
    parser.add_argument("query", help="Search query (e.g., 'modern leather chair')")
    parser.add_argument("--store-id", default="asset-metadata-store_1774257543650", help="Vertex AI Data Store ID")
    args = parser.parse_args()
    
    credentials = setup_credentials()
    project_number = "952613857720"
    
    search(args.query, credentials, project_number, args.store_id)

if __name__ == "__main__":
    main()
