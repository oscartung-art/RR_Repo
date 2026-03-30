import unittest
import os
import csv
import sys
import shutil

# Add the tools directory to the path so we can import the script
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
import update_project_index

class TestUpdateProjectIndex(unittest.TestCase):
    def setUp(self):
        # Create a temporary mock index file
        self.test_index = "tests/mock_index.csv"
        self.test_header = ["Code", "Project Name", "Client", "F: Drive Path", "Share Link"]
        with open(self.test_index, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.test_header)
            writer.writeheader()
            writer.writerow({
                "Code": "TEST123",
                "Project Name": "Test Project",
                "Client": "Test Client",
                "F: Drive Path": "F:/TEST123",
                "Share Link": "http://link.com"
            })

    def tearDown(self):
        # Clean up mock file
        if os.path.exists(self.test_index):
            os.remove(self.test_index)

    def test_load_index(self):
        # This should fail if the script still hardcodes "knowledge/"
        projects = update_project_index.load_index(self.test_index)
        self.assertIn("TEST123", projects)
        self.assertEqual(projects["TEST123"]["Project Name"], "Test Project")

    def test_save_index(self):
        projects = {
            "NEW456": {
                "Code": "NEW456",
                "Project Name": "New Project",
                "Client": "New Client",
                "F: Drive Path": "F:/NEW456",
                "Share Link": "-"
            }
        }
        update_project_index.save_index(self.test_index, projects)
        
        # Verify saved content
        reloaded = update_project_index.load_index(self.test_index)
        self.assertIn("NEW456", reloaded)
        self.assertEqual(reloaded["NEW456"]["Project Name"], "New Project")

    def test_process_file_with_table(self):
        # Create a mock Markdown file with a table
        test_md = "tests/mock_brief.md"
        content = """
| Field | Value |
| :--- | :--- |
| Name | KIL11285 SkyView |
| Client | Sino Land |
| RenderingShareDriveUrl | http://real-hk.com/drive |
"""
        with open(test_md, 'w', encoding='utf-8') as f:
            f.write(content)
        
        extracted = update_project_index.process_file(test_md)
        self.assertEqual(extracted["Project Name"], "KIL11285 SkyView")
        self.assertEqual(extracted["Client"], "Sino Land")
        self.assertEqual(extracted["Share Link"], "http://real-hk.com/drive")
        
        os.remove(test_md)

    def test_process_file_with_key_value(self):
        # Create a mock Markdown file with key-value pairs
        test_md = "tests/mock_brief_kv.md"
        content = """
**ProjectName**
KIL11285 Ground Floor

**Client**
Sino Administration

ProjectAddress
"Nos. 44 to 54A Wing Kwong Street"
"""
        with open(test_md, 'w', encoding='utf-8') as f:
            f.write(content)
        
        extracted = update_project_index.process_file(test_md)
        self.assertEqual(extracted["Project Name"], "KIL11285 Ground Floor")
        self.assertEqual(extracted["Client"], "Sino Administration")
        
        os.remove(test_md)

if __name__ == '__main__':
    unittest.main()
