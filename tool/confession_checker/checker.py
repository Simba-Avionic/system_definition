import os
import json
import logging
import sys
from typing import Dict, List, Optional


class SomeIpEntity:
    def __init__(self, service_name: str, service_id: int):
        self.service_name = service_name
        self.service_id = service_id
        self.methods: Dict[int, str] = {}
        self.events: Dict[int, str] = {}


class DiagEntity:
    def __init__(self, name: str):
        self.name = name
        self.jobs: Dict[int, str] = {}
        self.dtcs: Dict[int, str] = {}


class DataBase:
    def __init__(self) -> None:
        self.someip_db: Dict[int, SomeIpEntity] = {}
        self.diag_entities: List[DiagEntity] = []

        self.global_diag_job_ids: Dict[int, str] = {}
        self.global_diag_dtc_ids: Dict[int, str] = {}

    def add_someip_entity(self, entity: SomeIpEntity):
        if entity.service_id in self.someip_db:
            dup = self.someip_db[entity.service_id]
            error_msg = (
                f"Duplicate SOME/IP Service ID {entity.service_id}: "
                f"'{entity.service_name}' conflicts with '{dup.service_name}'"
            )
            logging.error(error_msg)
            raise ValueError(error_msg)
        self.someip_db[entity.service_id] = entity

    def add_diag_entity(self, entity: DiagEntity):
        for job_id, job_name in entity.jobs.items():
            if job_id in self.global_diag_job_ids:
                prev_name = self.global_diag_job_ids[job_id]
                error_msg = f"Duplicate Diag Job ID {job_id}: '{job_name}' conflicts with '{prev_name}'"
                logging.error(error_msg)
                raise ValueError(error_msg)
            self.global_diag_job_ids[job_id] = job_name

        for dtc_id, dtc_name in entity.dtcs.items():
            if dtc_id in self.global_diag_dtc_ids:
                prev_name = self.global_diag_dtc_ids[dtc_id]
                error_msg = f"Duplicate Diag DTC ID {dtc_id}: '{dtc_name}' conflicts with '{prev_name}'"
                logging.error(error_msg)
                raise ValueError(error_msg)
            self.global_diag_dtc_ids[dtc_id] = dtc_name

        self.diag_entities.append(entity)


def process_someip_data(data: dict) -> List[SomeIpEntity]:
    entities = []
    someip_content = data.get("someip", {})

    for service_name, service_data in someip_content.items():
        if "service_id" not in service_data:
            continue

        service_id = service_data["service_id"]
        entity = SomeIpEntity(service_name, service_id)

        methods = service_data.get("methods", {})
        events = service_data.get("events", {})

        for method_name, method_info in methods.items():
            method_id = method_info.get("id")
            if method_id is not None:
                if method_id in entity.methods:
                    error_msg = f"Duplicate Method ID {method_id} inside service {service_name}"
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                entity.methods[method_id] = method_name

        for event_name, event_info in events.items():
            event_id = event_info.get("id")
            if event_id is not None:
                if event_id in entity.events:
                    error_msg = f"Duplicate Event ID {event_id} inside service {service_name}"
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                entity.events[event_id] = event_name

        entities.append(entity)
    return entities


def process_diag_data(data: dict, filename: str) -> Optional[DiagEntity]:
    diag_content = data.get("diag", {})
    if not diag_content:
        return None

    entity = DiagEntity(name=filename)

    jobs = diag_content.get("job", {})
    for job_name, job_info in jobs.items():
        job_id = job_info.get("sub_service_id")
        if job_id is not None:
            if job_id in entity.jobs:
                error_msg = f"Duplicate Job ID {job_id} in file {filename}"
                logging.error(error_msg)
                raise ValueError(error_msg)
            entity.jobs[job_id] = job_name

    dtcs = diag_content.get("dtc", {})
    for dtc_name, dtc_info in dtcs.items():
        dtc_id = dtc_info.get("id")
        if dtc_id is not None:
            if dtc_id in entity.dtcs:
                error_msg = f"Duplicate DTC ID {dtc_id} in file {filename}"
                logging.error(error_msg)
                raise ValueError(error_msg)
            entity.dtcs[dtc_id] = dtc_name

    return entity


def validate_directory_content(filename: str, data: dict):
    path_parts = os.path.normpath(filename).split(os.sep)

    if "someip" in path_parts:
        if "someip" not in data:
            error_msg = f"File '{filename}' resides in a 'someip' folder but is missing the 'someip' key."
            logging.error(error_msg)
            raise ValueError(error_msg)

    if "diag" in path_parts:
        if "diag" not in data:
            error_msg = f"File '{filename}' resides in a 'diag' folder but is missing the 'diag' key."
            logging.error(error_msg)
            raise ValueError(error_msg)


def load_and_parse_file(filename: str, db: DataBase):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except json.JSONDecodeError:
        error_msg = f"Failed to decode JSON: {filename}"
        logging.error(error_msg)
        raise ValueError("JSON Decode Error")

    validate_directory_content(filename, data)

    if "someip" in data:
        try:
            someip_entities = process_someip_data(data)
            for entity in someip_entities:
                db.add_someip_entity(entity)
        except ValueError as e:
            # Note: logging is already handled inside the functions above
            raise e

    if "diag" in data:
        try:
            diag_entity = process_diag_data(data, filename)
            if diag_entity:
                db.add_diag_entity(diag_entity)
        except ValueError as e:
            # Note: logging is already handled inside the functions above
            raise e


def get_json_files(directory: str) -> List[str]:
    json_files = []
    if not os.path.exists(directory):
        logging.warning(f"Directory not found: {directory}")
        return []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = DataBase()

    # Define the directories to scan explicitly
    target_dirs = ["./someip", "./diag"]

    has_error = False

    for folder_path in target_dirs:
        logging.info(f"--- Scanning directory: {folder_path} ---")
        json_files = get_json_files(folder_path)

        for json_file in json_files:
            logging.info(f"Processing file: {json_file}")
            try:
                load_and_parse_file(json_file, db)
            except ValueError as e:
                logging.error(f"FAILED to process {json_file}")
                has_error = True

    if has_error:
        logging.error("Validation failed. Errors were found in configuration files.")
        sys.exit(1)
    else:
        logging.info("Validation successful. All files are correct.")
        sys.exit(0)