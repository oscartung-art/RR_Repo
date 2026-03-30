import unittest
import os
import shutil
import sys
import json
import csv

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
import sync_assets

class TestSyncAssets(unittest.TestCase):
    def setUp(self):
        # Setup mock directories
        self.test_dir = "tests/temp_asset_env"
        self.mock_g_drive = os.path.join(self.test_dir, "G_Drive")
        self.mock_d_drive = os.path.join(self.test_dir, "D_Drive_Thumbnails")
        self.mock_db_dir = os.path.join(self.test_dir, "db")
        
        os.makedirs(self.mock_g_drive, exist_ok=True)
        os.makedirs(self.mock_d_drive, exist_ok=True)
        os.makedirs(self.mock_db_dir, exist_ok=True)
        
        # Create a mock asset on G: Drive
        # Convention: [Category]_[Source]_[Description]_[ID]
        self.asset_name = "Furniture_Maxtree_OakTable_MT001"
        self.asset_zip = os.path.join(self.mock_g_drive, f"{self.asset_name}.zip")
        self.asset_jpg = os.path.join(self.mock_g_drive, f"{self.asset_name}.jpg")
        
        with open(self.asset_zip, 'w') as f: f.write("mock zip content")
        with open(self.asset_jpg, 'w') as f: f.write("mock jpg content")
        
        # Mock Master Asset Index
        self.mock_index_csv = os.path.join(self.mock_db_dir, "Asset_Index.csv")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_parse_filename(self):
        filename = "Furniture_Maxtree_OakTable_MT001.zip"
        data = sync_assets.parse_filename(filename)
        self.assertEqual(data["Category"], "Furniture")
        self.assertEqual(data["Source"], "Maxtree")
        self.assertEqual(data["Description"], "OakTable")
        self.assertEqual(data["ID"], "MT001")
        
    def test_generate_sidecar_json(self):
        data = {"Category": "Furniture", "Source": "Maxtree", "Description": "OakTable", "ID": "MT001"}
        json_path = os.path.join(self.mock_g_drive, f"{self.asset_name}.json")
        
        sync_assets.generate_sidecar_json(json_path, data)
        
        self.assertTrue(os.path.exists(json_path))
        with open(json_path, 'r') as f:
            saved_data = json.load(f)
            self.assertEqual(saved_data["ID"], "MT001")

    def test_mirror_thumbnail(self):
        # Should copy the JPG from G: to D:
        sync_assets.mirror_thumbnail(self.asset_jpg, self.mock_d_drive)
        mirrored_jpg = os.path.join(self.mock_d_drive, f"{self.asset_name}.jpg")
        self.assertTrue(os.path.exists(mirrored_jpg))

    def test_update_asset_index(self):
        data = [{"Category": "Furniture", "Source": "Maxtree", "Description": "OakTable", "ID": "MT001"}]
        sync_assets.update_asset_index(self.mock_index_csv, data)
        
        self.assertTrue(os.path.exists(self.mock_index_csv))
        with open(self.mock_index_csv, 'r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 1)
            self.assertEqual(reader[0]["ID"], "MT001")

if __name__ == '__main__':
    unittest.main()
