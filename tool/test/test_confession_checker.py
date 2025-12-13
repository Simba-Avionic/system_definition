import unittest
# Import the classes and functions from your main file
from tool.confession_checker.checker import (
    DataBase,
    SomeIpEntity,
    process_someip_data,
    process_diag_data
)


class TestJsonProcessing(unittest.TestCase):

    def setUp(self):
        self.db = DataBase()


    def test_valid_someip(self):
        """Test parsing a standard valid SOME/IP structure."""
        data = {
            "someip": {
                "EngineService": {
                    "service_id": 100,
                    "methods": {"Start": {"id": 1}},
                    "events": {"Status": {"id": 32000}}
                }
            }
        }
        entities = process_someip_data(data)
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].service_id, 100)
        self.assertEqual(entities[0].methods[1], "Start")
        # Ensure it can be added to DB
        self.db.add_someip_entity(entities[0])

    def test_duplicate_someip_service_id(self):
        """Test that two services with the same ID raise an error."""
        ent1 = SomeIpEntity("ServiceA", 100)
        ent2 = SomeIpEntity("ServiceB", 100)

        self.db.add_someip_entity(ent1)

        with self.assertRaises(ValueError):
            self.db.add_someip_entity(ent2)

    def test_duplicate_someip_method_id_internal(self):
        """Test that duplicate method IDs within one service raise an error."""
        data = {
            "someip": {
                "BadService": {
                    "service_id": 200,
                    "methods": {
                        "MethodA": {"id": 10},
                        "MethodB": {"id": 10}  # Duplicate ID
                    }
                }
            }
        }
        with self.assertRaises(ValueError):
            process_someip_data(data)

    # --- Diag Tests ---

    def test_valid_diag_job(self):
        """Test parsing a valid Diag Job (DID)."""
        data = {
            "diag": {
                "job": {
                    "read_did_1": {"sub_service_id": 0x1234}
                }
            }
        }
        entity = process_diag_data(data, "test_file.json")
        self.db.add_diag_entity(entity)

        # Check global registry
        self.assertIn(0x1234, self.db.global_diag_job_ids)

    def test_valid_diag_dtc(self):
        """Test parsing a valid Diag DTC."""
        data = {
            "diag": {
                "dtc": {
                    "engine_overheat": {"id": 123456}
                }
            }
        }
        entity = process_diag_data(data, "test_file.json")
        self.db.add_diag_entity(entity)
        self.assertIn(123456, self.db.global_diag_dtc_ids)

    def test_duplicate_diag_job_id_global(self):
        """Test collision of Diag Job IDs across two different files."""
        # File 1 processing
        data1 = {"diag": {"job": {"jobA": {"sub_service_id": 10}}}}
        entity1 = process_diag_data(data1, "file1.json")
        self.db.add_diag_entity(entity1)

        # File 2 processing (conflict)
        data2 = {"diag": {"job": {"jobB": {"sub_service_id": 10}}}}
        entity2 = process_diag_data(data2, "file2.json")

        with self.assertRaises(ValueError):
            self.db.add_diag_entity(entity2)

    def test_duplicate_diag_dtc_id_global(self):
        """Test collision of Diag DTC IDs across two different files."""
        # File 1 processing
        data1 = {"diag": {"dtc": {"faultA": {"id": 999}}}}
        entity1 = process_diag_data(data1, "file1.json")
        self.db.add_diag_entity(entity1)

        # File 2 processing (conflict)
        data2 = {"diag": {"dtc": {"faultB": {"id": 999}}}}
        entity2 = process_diag_data(data2, "file2.json")

        with self.assertRaises(ValueError):
            self.db.add_diag_entity(entity2)

    # --- General Tests ---

    def test_mixed_content_ignored(self):
        """Test that unrelated JSON content returns None/Empty safely."""
        data = {"other_config": {}}
        someip = process_someip_data(data)
        diag = process_diag_data(data, "test.json")

        self.assertEqual(someip, [])
        self.assertIsNone(diag)


if __name__ == '__main__':
    unittest.main()