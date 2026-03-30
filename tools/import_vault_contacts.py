import os
import re
import csv
import io

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Shared.config import PROJECT_ROOT, BRAIN_ROOT

# Paths
VAULT_PROJECT_DIR = str(PROJECT_ROOT)  # F:\Projects (NAS project mass)
CRM_PATH = str(BRAIN_ROOT / "db" / "Master_CRM.csv")

def load_existing_contacts(csv_path):
    contacts = []
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contacts.append(row)
    return contacts

def save_contacts(csv_path, contacts):
    if not contacts:
        return
    
    header = ["Company", "Person", "Email", "Phone", "Address", "Tags", "Note"]
    
    # Sort by Company
    contacts.sort(key=lambda x: (x.get("Company") or "").lower())
    
    with open(csv_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(contacts)

def parse_markdown_table(content):
    rows = []
    # Find tables
    table_pattern = re.compile(r'\|(.+)\|[\r\n]+\|([- |]+)\|[\r\n]+((?:\|.+\|[\r\n]*)+)')
    matches = table_pattern.findall(content)
    
    for match in matches:
        header_row = match[0].split('|')
        data_rows = match[2].strip().split('\n')
        
        headers = [h.strip() for h in header_row if h.strip()]
        
        for dr in data_rows:
            cols = [c.strip() for c in dr.split('|') if c.strip()]
            if len(cols) >= 2:
                rows.append({cols[0]: cols[1]})
            elif len(cols) == len(headers):
                 rows.append(dict(zip(headers, cols)))
                 
    return rows

def parse_key_value(content):
    data = {}
    # Find lines like "Key : Value" or "Key: Value"
    kv_pattern = re.compile(r'^([^:\n]+)\s*:\s*(.+)$', re.MULTILINE)
    matches = kv_pattern.findall(content)
    for k, v in matches:
        data[k.strip()] = v.strip()
    return data

def clean_text(text):
    if not text: return ""
    # Remove HTML tags like <br>
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove markdown bold/italic
    text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    # Remove leading/trailing punctuation and spaces
    text = text.strip().strip(",").strip(";")
    return text

def normalize_identifier(text):
    if not text: return ""
    # Remove spaces, punctuation, lowercase
    return re.sub(r'[\s\W_]+', '', text).lower()

def normalize_phone(text):
    if not text: return ""
    # Remove non-numeric except + and () and -
    return re.sub(r'[^\d+\(\)\-\s]', '', text).strip()

def extract_email(text):
    if not text: return ""
    # Handle markdown links like [email](mailto:email)
    match = re.search(r'\[?([^\]]+)\]?\(mailto:([^\)]+)\)', text)
    if match:
        return match.group(2).strip()
    # Simple regex for email
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if match:
        return match.group(0).strip()
    return text.strip()

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

    found_contacts = []
    
    # Try table parsing
    table_data = parse_markdown_table(content)
    if table_data:
        contact_dict = {}
        for item in table_data:
            for k, v in item.items():
                contact_dict[k] = v
        
        # Check if it has client info
        if any(k in contact_dict for k in ["ClientCompanyName", "ClientEmail", "Company", "Architect", "InteriorDesign"]):
            c = {"Tags": "Imported", "Note": f"From {os.path.basename(file_path)}"}
            c["Company"] = clean_text(contact_dict.get("ClientCompanyName") or contact_dict.get("Company") or "")
            c["Person"] = clean_text(contact_dict.get("Person") or contact_dict.get("Contact Person") or contact_dict.get("Attn") or "")
            c["Email"] = extract_email(contact_dict.get("ClientEmail") or contact_dict.get("Email") or "")
            c["Phone"] = normalize_phone(contact_dict.get("ClientPhoneNumber") or contact_dict.get("Phone") or "")
            c["Address"] = clean_text(contact_dict.get("ClientAddress") or contact_dict.get("Address") or "")
            
            if c["Company"] or c["Person"] or c["Email"]:
                found_contacts.append(c)
            
            # Professionals
            for prof in ["Architect", "InteriorDesign", "Landscape", "Structure"]:
                prof_name = contact_dict.get(prof)
                if prof_name and prof_name not in ["-", "TBC", "N/A"]:
                    pc = {"Company": clean_text(prof_name), "Person": "", "Email": "", "Phone": "", "Address": "", "Tags": "Imported", "Note": f"{prof} from {os.path.basename(file_path)}"}
                    found_contacts.append(pc)

    # Try Key-Value parsing
    kv_data = parse_key_value(content)
    if kv_data:
        c = {"Tags": "Imported", "Note": f"From {os.path.basename(file_path)}"}
        c["Company"] = clean_text(kv_data.get("The Client") or kv_data.get("The Consultant") or kv_data.get("Company") or kv_data.get("Client") or "")
        c["Person"] = clean_text(kv_data.get("Attn") or kv_data.get("Person") or kv_data.get("Name") or "")
        c["Email"] = extract_email(kv_data.get("Email") or "")
        c["Phone"] = normalize_phone(kv_data.get("Phone") or kv_data.get("General Line") or "")
        c["Address"] = clean_text(kv_data.get("Address") or "")
        
        if c["Company"] or c["Person"] or c["Email"]:
            if not any(normalize_identifier(fc["Company"]) == normalize_identifier(c["Company"]) and extract_email(fc["Email"]) == extract_email(c["Email"]) for fc in found_contacts):
                found_contacts.append(c)

    return found_contacts

def main():
    existing_contacts = load_existing_contacts(CRM_PATH)
    new_contacts = []
    
    seen_identifiers = set()
    for ec in existing_contacts:
        email_ident = extract_email(ec.get("Email", "")).lower().strip()
        comp_pers_ident = normalize_identifier((ec.get("Company") or "") + (ec.get("Person") or ""))
        if email_ident: seen_identifiers.add(email_ident)
        if comp_pers_ident: seen_identifiers.add(comp_pers_ident)

    print(f"Scanning {VAULT_PROJECT_DIR}...")
    for root, dirs, files in os.walk(VAULT_PROJECT_DIR):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                extracted = process_file(file_path)
                for c in extracted:
                    email_ident = extract_email(c.get("Email", "")).lower().strip()
                    comp_pers_ident = normalize_identifier((c.get("Company") or "") + (c.get("Person") or ""))
                    
                    is_new = True
                    if email_ident and email_ident in seen_identifiers: is_new = False
                    if comp_pers_ident and comp_pers_ident in seen_identifiers: is_new = False
                    
                    if is_new:
                        new_contacts.append(c)
                        if email_ident: seen_identifiers.add(email_ident)
                        if comp_pers_ident: seen_identifiers.add(comp_pers_ident)
                        print(f"Found new contact: {c['Company']} / {c['Person']}")

    if new_contacts:
        print(f"Found {len(new_contacts)} new contacts. Appending to {CRM_PATH}...")
        all_contacts = existing_contacts + new_contacts
        save_contacts(CRM_PATH, all_contacts)
    else:
        print("No new contacts found.")

if __name__ == "__main__":
    main()
