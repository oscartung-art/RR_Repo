import os
import sys
import csv

# Define project root relative to the script's location (tools/ folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRM_PATH = os.path.join(PROJECT_ROOT, "db", "Master_CRM.csv")

def view_crm(search_query=None):
    if not os.path.exists(CRM_PATH):
        print(f"\033[91mError: CRM file not found at {CRM_PATH}\033[0m")
        return

    contacts = []
    with open(CRM_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            given = row.get('Given Name', '').strip()
            family = row.get('Family Name', '').strip()
            name = f"{given} {family}".strip()
            org = row.get('Organization', '').strip() or "-"
            email = row.get('Email', '').strip() or "-"
            phone = row.get('Phone', '').strip() or "-"
            
            # Simple text search filter
            if search_query:
                search_str = f"{name} {org} {email} {phone}".lower()
                if search_query.lower() not in search_str:
                    continue
                    
            contacts.append((name, org, email, phone))
            
    if not contacts:
        if search_query:
            print(f"\n\033[90mNo contacts found matching '{search_query}'.\033[0m\n")
        else:
            print("\n\033[90mCRM is empty.\033[0m\n")
        return

    # Determine dynamic column widths based on the longest string in each column
    max_name = max([len(c[0]) for c in contacts] + [20])
    max_org = max([len(c[1]) for c in contacts] + [15])
    max_email = max([len(c[2]) for c in contacts] + [25])
    
    title = f"=== MASTER CRM ({len(contacts)} Contacts) ==="
    if search_query:
        title = f"=== CRM SEARCH: '{search_query}' ({len(contacts)} Results) ==="

    print(f"\n\033[1;32m{title}\033[0m")
    
    # Header
    print(f"  \033[1;37m{'NAME':<{max_name}} | {'ORGANIZATION':<{max_org}} | {'EMAIL':<{max_email}} | PHONE\033[0m")
    print(f"  \033[90m{'-'*max_name}-+-{'-'*max_org}-+-{'-'*max_email}-+-------------------\033[0m")
    
    # Sort contacts alphabetically by Organization, then by Name
    contacts.sort(key=lambda x: (x[1].lower(), x[0].lower()))
    
    for name, org, email, phone in contacts:
        # Highlight values, dim missing values
        d_org = f"\033[33m{org:<{max_org}}\033[0m" if org != "-" else f"\033[90m{org:<{max_org}}\033[0m"
        d_email = f"\033[36m{email:<{max_email}}\033[0m" if email != "-" else f"\033[90m{email:<{max_email}}\033[0m"
        d_phone = phone if phone != "-" else f"\033[90m-\033[0m"
        
        print(f"  {name:<{max_name}} | {d_org} | {d_email} | {d_phone}")
        
    print("\n\033[90mTo edit, open: db/Master_CRM.csv\033[0m\n")

if __name__ == "__main__":
    # If an argument is provided, treat it as a search query
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    view_crm(query)
