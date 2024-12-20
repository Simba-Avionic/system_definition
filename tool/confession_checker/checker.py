import os
import json
import logging
from typing import Dict, List, Optional


class Entity:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.methods: Dict[int, str] = {}
        self.events: Dict[int, str] = {}


class DataBase:
    def __init__(self) -> None:
        self.db: Dict[int, Entity] = {}

    def add_to_db(self, id: int, entity: Entity):
        if id in self.db:
            dup = self.db[id]
            logging.error(
                f"Duplicate object with ID {id} found: {entity.service_name} conflicts with {dup.service_name}"
            )
            exit(1)
        self.db[id] = entity


def get_json_files(directory: str) -> List[str]:
    """Retrieve all JSON files in the given directory and its subdirectories."""
    json_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files


def load_json(filename: str):
    """Load and parse a JSON file into Entity objects."""
    with open(filename, 'r') as file:
        data = json.load(file)

        # Access the "someip" key
        someip_data = data.get("someip", {})
        if not someip_data:
            logging.error(f"No 'someip' key found in file {filename}")
            return None, None

        # Extract the first service (e.g., "ServoService")
        service_name = next(iter(someip_data.keys()))
        service_data = someip_data[service_name]

        service_id = service_data["service_id"]
        methods = service_data.get("methods", {})
        events = service_data.get("events", {})

        entity = Entity(service_name)

        # Process methods
        for method_name, method_info in methods.items():
            method_id = method_info["id"]
            if method_id in entity.methods:
                logging.error(
                    f"Duplicate method ID {method_id} for method {method_name} and {entity.methods[method_id]}"
                )
                exit(1)
            entity.methods[method_id] = method_name

        # Process events
        for event_name, event_info in events.items():
            event_id = event_info["id"]
            if event_id in entity.events:
                logging.error(
                    f"Duplicate event ID {event_id} for event {event_name} and {entity.events[event_id]}"
                )
                exit(1)
            entity.events[event_id] = event_name

        return service_id, entity


# Main usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = DataBase()
    folder_path = "./someip"  # Directory containing JSON files

    json_files = get_json_files(folder_path)
    for json_file in json_files:
        logging.info(f"Processing file: {json_file}")
        service_id, entity = load_json(json_file)
        if (service_id is not None and entity is not None):
            db.add_to_db(service_id, entity)
