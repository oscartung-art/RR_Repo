import os
import re
import csv
import sys
import argparse
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Define paths
REPO_ROOT = r"D:\GoogleDrive\RR_Repo"
CRM_CSV_PATH = os.path.join(REPO_ROOT, "db", "Master_CRM.csv")
SHARED_PATH = os.path.join(REPO_ROOT, "Shared")
SERVICE_ACCOUNT_FILE = os.path.join(SHARED_PATH, "service-account.json")
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/contacts'
]

def to_title_case(s):
    """Converts a string to Standard Title Case."""
    return ' '.join(word.capitalize() for word in re.split(r'[\s_-]+', s)) if s else ''

def sanitize_phone_number(phone):
    """Ensures phone numbers have the +852 prefix if they are HK numbers."""
    if phone and len(phone) == 8 and phone.isdigit():
        return f"+852 {phone}"
    return phone

def get_service(user_email):
    """Authenticates using a service account and returns the People and Gmail API services."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        delegated_creds = creds.with_subject(user_email)
        
        people_service = build('people', 'v1', credentials=delegated_creds)
        gmail_service = build('gmail', 'v1', credentials=delegated_creds)
        
        return people_service, gmail_service
    except Exception as e:
        print(f"❌ Error creating services for {user_email}: {e}")
        return None, None

def enrich_from_emails(gmail_service, existing_contacts):
    """
    Scans sent emails to discover new contacts and enrich existing ones.
    This function is NON-DESTRUCTIVE: it only fills in blank fields.
    """
    print("Performing non-destructive deep scan of sent emails...")
    newly_discovered_count = 0
    
    try:
        results = gmail_service.users().messages().list(userId='me', q='in:sent', maxResults=500).execute()
        messages = results.get('messages', [])
        if not messages:
            print("  No sent messages found.")
            return existing_contacts, 0

        print(f"  Analyzing {len(messages)} email threads...")
        
        for msg in messages:
            msg_data = gmail_service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = msg_data['payload']['headers']
            
            participants = []
            for header in headers:
                if header['name'].lower() in ['to', 'from', 'cc']:
                    matches = re.findall(r'([\w\s,]+)<([^>]+)>', header['value'])
                    for name, email in matches:
                        participants.append({'name': name.strip(), 'email': email.strip().lower()})

            for person in participants:
                email = person['email']
                if 'real-hk.com' in email:
                    continue

                # --- The "Enrich, Don't Replace" Logic ---
                
                # Check if contact exists. If not, create a new, blank entry.
                if email not in existing_contacts:
                    newly_discovered_count += 1
                    name_parts = person['name'].split()
                    existing_contacts[email] = {
                        'Given Name': to_title_case(name_parts[0] if name_parts else ''),
                        'Family Name': to_title_case(' '.join(name_parts[1:]) if len(name_parts) > 1 else ''),
                        'Organization': '', 'Email': email, 'Phone': '',
                        'Notes': '', 'Group Membership': 'Gmail Discovered', 'Website': ''
                    }

                # Get the authoritative record (either existing or the one we just created)
                contact_record = existing_contacts[email]

                # Now, only fill in the blanks.
                if not contact_record.get('Organization'):
                    domain = email.split('@')[1]
                    company_name = domain.split('.')[0]
                    contact_record['Organization'] = to_title_case(company_name)
                    
                if 'payload' in msg_data and 'body' in msg_data['payload'] and 'data' in msg_data['payload']['body']:
                    import base64
                    body = base64.urlsafe_b64decode(msg_data['payload']['body']['data']).decode('utf-8')
                    
                    if not contact_record.get('Website'):
                        website_match = re.search(r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', body)
                        if website_match:
                            contact_record['Website'] = website_match.group(0)

                    if not contact_record.get('Phone'):
                        phone_match = re.search(r'(\+?\d{1,3}[\s-]?\d{4}[\s-]?\d{4})', body) # More specific phone regex
                        if phone_match:
                            contact_record['Phone'] = sanitize_phone_number(phone_match.group(0))
                            
    except Exception as e:
        print(f"  ⚠️ An error occurred during email processing: {e}")

    return existing_contacts, newly_discovered_count

def main(users, sweep=False, push=False):
    """Main function to perform CRM operations for specified user(s)."""
    
    # 1. Load local CRM
    if not os.path.exists(CRM_CSV_PATH):
        print(f"File not found: {CRM_CSV_PATH}. Starting with an empty CRM.")
        local_contacts = {}
    else:
        with open(CRM_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            local_contacts = {row['Email'].lower(): row for row in reader}

    for user_email in users:
        print(f"\n--- Processing for user: {user_email} ---")
        people_service, gmail_service = get_service(user_email)
        
        if not people_service or not gmail_service:
            continue

        # Run the deep enrichment from emails
        local_contacts, new_found = enrich_from_emails(gmail_service, local_contacts)
        print(f"  Found {new_found} new potential contacts from emails.")
        
        # Optionally, you can add the --sweep and --push logic here
        # For now, we are just demonstrating the multi-user capability
        
    # 3. Write final, enriched CSV
    print("\nWriting final enriched data to Master_CRM.csv...")
    fieldnames = ['Given Name', 'Family Name', 'Organization', 'Email', 'Phone', 'Notes', 'Group Membership', 'Website']
    try:
        with open(CRM_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            # Filter out any potential malformed rows (e.g., empty rows) before sorting and writing
            valid_contacts = [contact for contact in local_contacts.values() if contact and contact.get('Email')]
            writer.writerows(sorted(valid_contacts, key=lambda x: x.get('Given Name', '')))
        print(f"✅ Successfully wrote {len(local_contacts)} contacts to {CRM_CSV_PATH}")
    except IOError as e:
        print(f"❌ Error writing to CSV: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""
    Synchronize CRM with Google Contacts and enrich from emails for one or more users.
    Requires a service-account.json with domain-wide delegation.
    """)
    parser.add_argument(
        '--users',
        nargs='+',
        required=True,
        help="The email address(es) of the user(s) to process (e.g., user1@example.com user2@example.com)."
    )
    # Add back --sweep and --push if their logic is reimplemented
    
    args = parser.parse_args()
    main(users=args.users)
