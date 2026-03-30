import unittest
import os
import shutil
import sys
import csv
from unittest.mock import patch, MagicMock

# Add the tools directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
import new_project

class TestNewProjectSpawner(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_test_env"
        self.test_db_dir = os.path.join(self.test_dir, "db")
        self.test_f_drive = os.path.join(self.test_dir, "F_Drive")
        
        os.makedirs(self.test_db_dir, exist_ok=True)
        os.makedirs(self.test_f_drive, exist_ok=True)
        
        # Mock index CSV
        self.mock_index_csv = os.path.join(self.test_db_dir, "Project_Master_Index.csv")
        self.headers = ["Code", "Project Name", "Client", "F: Drive Path", "Share Link"]
        with open(self.mock_index_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            writer.writerow(["OLD001", "Old Project", "Old Client", "F:/OLD001_OldProject", "-"])

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_generate_folder_structure(self):
        project_code = "TEST001"
        project_name = "Test Project"
        target_path = os.path.join(self.test_f_drive, f"{project_code}_{project_name.replace(' ', '')}")
        
        new_project.generate_folder_structure(target_path)
        
        # Verify Flat 3 Structure
        self.assertTrue(os.path.exists(os.path.join(target_path, "01_Brief")))
        self.assertTrue(os.path.exists(os.path.join(target_path, "02_Work")))
        self.assertTrue(os.path.exists(os.path.join(target_path, "03_Shared")))

    def test_update_master_database(self):
        project_code = "TEST002"
        project_name = "Test Project 2"
        client = "Test Client"
        f_drive_path = "F:/TEST002_TestProject2"
        
        new_project.update_master_database(self.mock_index_csv, project_code, project_name, client, f_drive_path)
        
        # Verify CSV was appended correctly without overwriting
        with open(self.mock_index_csv, 'r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 2)
            self.assertEqual(reader[1]["Code"], "TEST002")
            self.assertEqual(reader[1]["Project Name"], "Test Project 2")
            self.assertEqual(reader[1]["Client"], "Test Client")

    @patch('subprocess.run')
    def test_create_github_issue(self, mock_subprocess):
        # Mocking the gh cli call
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        project_code = "TEST003"
        project_name = "Test Issue Project"
        client = "Client A"
        f_drive_path = "F:/TEST003_TestIssueProject"
        
        success = new_project.create_github_issue(project_code, project_name, client, f_drive_path)
        self.assertTrue(success)
        mock_subprocess.assert_called_once()
        
        # Check that the command passed to subprocess contains 'gh' and 'issue create'
        args = mock_subprocess.call_args[0][0]
        self.assertIn('gh', args)
        self.assertIn('issue', args)
        self.assertIn('create', args)

if __name__ == '__main__':
    unittest.main()
