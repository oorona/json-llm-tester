import requests
import json
import time
import os
import shutil
from datetime import datetime
from typing import Optional # Added for type hinting

# --- Configuration ---
BASE_URL = "http://localhost:8000"
EXPECTED_PYTHON_ENV = "development" 
DATABASE_FILENAME = f"{EXPECTED_PYTHON_ENV}_llm_evaluator.db"
DATABASE_FILE_PATH = os.path.join("backend", DATABASE_FILENAME) # Assumes script is in project root

HEADERS = {
    "Content-Type": "application/json",
}

# --- Test Results Tracking ---
test_results = {"passed": 0, "failed": 0, "details": []}

# --- Globals for IDs to pass between tests ---
# These are set by test functions upon successful creation
created_example_id_global: Optional[int] = None
generated_schema_id_global: Optional[int] = None
approved_schema_id_for_linking: Optional[int] = None # Specifically for an approved schema
mock_data_prompt_id_global: Optional[int] = None
created_mock_item_ids_global: list = []
master_prompt_id_global: Optional[int] = None
test_run_id_global: Optional[int] = None 

# --- Helper Functions ---
def print_test_result(test_name: str, success: bool, message: str = ""):
    global test_results
    status = "PASS" if success else "FAIL"
    print(f"Test: {test_name} ... {status}")
    if message:
        print(f"     {message}")
    if success:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    test_results["details"].append({"name": test_name, "status": status, "message": message})
    print("-" * 30)

def print_response_summary(response: requests.Response):
    print(f"     Status Code: {response.status_code}")
    try:
        response_json = response.json()
        if isinstance(response_json, list):
            print(f"     Response JSON is a list with {len(response_json)} items.")
            if len(response_json) > 0 and len(str(response_json)) < 200:
                print(f"     List content: {json.dumps(response_json, indent=2)}")
            elif len(response_json) > 0:
                 print(f"     First item summary (keys if dict): {list(response_json[0].keys()) if isinstance(response_json[0], dict) else str(response_json[0])[:100]}")
        elif isinstance(response_json, dict):
            if len(str(response_json)) < 200:
                 print(f"     Response JSON: {json.dumps(response_json, indent=2)}")
            else:
                print(f"     Response JSON (keys): {list(response_json.keys())}")
        else: 
            print(f"     Response JSON: {json.dumps(response_json, indent=2)}")
    except json.JSONDecodeError:
        print(f"     Response Text (first 100 chars): {response.text[:100]}")

def backup_and_reset_database(db_path):
    print(f"\n--- Managing Database: {db_path} ---")
    db_dir = os.path.dirname(db_path)
    if not db_dir: # If db_path is just a filename, assume current dir
        db_dir = "."
    db_file_name_only = os.path.basename(db_path)

    if os.path.exists(db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir_name = "db_backups"
        backup_dir_path = os.path.join(db_dir, backup_dir_name)
        os.makedirs(backup_dir_path, exist_ok=True)
        
        base_name, ext = os.path.splitext(db_file_name_only)
        backup_filename = f"{base_name}_backup_{timestamp}{ext}"
        backup_file_full_path = os.path.join(backup_dir_path, backup_filename)

        try:
            print(f"Backing up existing database to: {backup_file_full_path}")
            shutil.copy2(db_path, backup_file_full_path)
            print("Backup successful.")
            print(f"Deleting current database file: {db_path}")
            os.remove(db_path)
            print("Database file deleted.")
            print("The FastAPI application will create a new, empty database on its next startup.")
        except Exception as e:
            print(f"Error during database backup/reset: {e}")
            print("Please check file permissions and paths. Halting script.")
            return False
    else:
        print(f"Database file '{db_path}' does not exist. A new one will be created by the FastAPI app.")
    print("-------------------------------------\n")
    return True

# --- Test Functions ---
def test_root():
    global approved_schema_id_for_linking # Ensure it's accessible if modified
    test_name = "GET / (Root)"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    try:
        response = requests.get(f"{BASE_URL}/", headers=HEADERS, timeout=5)
        print_response_summary(response)
        success = response.status_code == 200 and response.json().get("message") is not None
        message = "Root endpoint check." if success else f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_get_models():
    test_name = "GET /models"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    try:
        response = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=10)
        print_response_summary(response)
        success = response.status_code == 200 and isinstance(response.json(), list)
        message = f"Fetched {len(response.json())} models." if success else f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_list_json_examples(expected_min_count: int = 0):
    test_name = f"GET /json-examples/ (List All, expecting >={expected_min_count})"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    try:
        response = requests.get(f"{BASE_URL}/json-examples/", headers=HEADERS, timeout=10)
        print_response_summary(response)
        if response.status_code == 200:
            data = response.json()
            success = isinstance(data, list) and len(data) >= expected_min_count
            message = f"Listed {len(data)} examples." if success else f"Count mismatch or not a list. Got {len(data) if isinstance(data, list) else 'Not a list'}."
        else: message = f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)


def test_create_json_example():
    global created_example_id_global
    test_name = "POST /json-examples/"
    print(f"Starting Test: {test_name}")
    success = False; message = ""; created_example_id_global = None
    payload = {"content": {"name": "TestItemForSchema", "value": 123, "is_active": True}, "description": "Item for schema generation test"}
    try:
        response = requests.post(f"{BASE_URL}/json-examples/", headers=HEADERS, json=payload, timeout=10)
        print_response_summary(response)
        if response.status_code == 201 and response.json().get("id"):
            created_example_id_global = response.json().get("id")
            success = True; message = f"Example created with ID: {created_example_id_global}."
        else: message = f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_generate_schema():
    global generated_schema_id_global, created_example_id_global
    test_name = f"POST /json-examples/{created_example_id_global}/generate-schema"
    print(f"Starting Test: {test_name}")
    success = False; message = ""; generated_schema_id_global = None
    if not created_example_id_global:
        message = "Skipped: No example_id provided."
        print_test_result(test_name, False, message); print("=" * 30); return
    try:
        response = requests.post(f"{BASE_URL}/json-examples/{created_example_id_global}/generate-schema", headers=HEADERS, timeout=45)
        print_response_summary(response)
        if response.status_code == 201 and response.json().get("id"): # Assuming this endpoint returns schema details
            generated_schema_id_global = response.json().get("id")
            success = True; message = f"Schema generated with ID: {generated_schema_id_global}."
        elif response.status_code == 200 and response.json().get("id"): # Or 200 if it's an action on an existing resource
             generated_schema_id_global = response.json().get("id")
             success = True; message = f"Schema generated with ID: {generated_schema_id_global} (Status 200)."
        else: message = f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_list_json_schemas(expected_min_count: int = 0):
    test_name = f"GET /json-schemas/ (List All, expecting >={expected_min_count})"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    try:
        response = requests.get(f"{BASE_URL}/json-schemas/", headers=HEADERS, timeout=10)
        print_response_summary(response)
        if response.status_code == 200:
            data = response.json()
            success = isinstance(data, list) and len(data) >= expected_min_count
            message = f"Listed {len(data)} schemas." if success else f"Count mismatch or not a list. Got {len(data) if isinstance(data, list) else 'Not a list'}."
        else: message = f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_get_json_schema():
    global generated_schema_id_global
    test_name = f"GET /json-schemas/{generated_schema_id_global}"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not generated_schema_id_global:
        message = "Skipped: No schema_id provided."
        print_test_result(test_name, False, message); print("=" * 30); return
    try:
        response = requests.get(f"{BASE_URL}/json-schemas/{generated_schema_id_global}", headers=HEADERS, timeout=10)
        print_response_summary(response)
        success = response.status_code == 200 and response.json().get("id") == generated_schema_id_global
        message = f"Schema {generated_schema_id_global} retrieved." if success else f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_update_json_schema():
    global generated_schema_id_global
    test_name = f"PUT /json-schemas/{generated_schema_id_global} (General Update)"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not generated_schema_id_global:
        message = "Skipped: No schema_id provided."
        print_test_result(test_name, False, message); print("=" * 30); return
    payload = {"name": "UpdatedSchemaNameByScript", "status": "script_updated_status_generic"}
    try:
        response = requests.put(f"{BASE_URL}/json-schemas/{generated_schema_id_global}", headers=HEADERS, json=payload, timeout=10)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("name") == payload["name"]:
            success = True; message = f"Schema {generated_schema_id_global} updated with new name/status."
        else: message = f"Failed with status {response.status_code} or name mismatch."
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_refine_json_schema_with_llm():
    global generated_schema_id_global
    test_name = f"POST /json-schemas/{generated_schema_id_global}/refine-with-llm"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not generated_schema_id_global:
        message = "Skipped: No schema_id provided."
        print_test_result(test_name, False, message); print("=" * 30); return
    payload = {"feedback": "Ensure all top-level properties are explicitly listed in a 'required' array."}
    original_version = -1
    try:
        get_resp = requests.get(f"{BASE_URL}/json-schemas/{generated_schema_id_global}", headers=HEADERS, timeout=10)
        if get_resp.status_code == 200: original_version = get_resp.json().get("version", -1)
        
        response = requests.post(f"{BASE_URL}/json-schemas/{generated_schema_id_global}/refine-with-llm", headers=HEADERS, json=payload, timeout=60)
        print_response_summary(response)
        if response.status_code == 200:
            refined_schema = response.json()
            if refined_schema.get("id") == generated_schema_id_global and (original_version == -1 or refined_schema.get("version", -1) > original_version):
                success = True; message = f"Schema {generated_schema_id_global} refined to version {refined_schema.get('version')}."
            else: message = f"Refinement OK (200) but version unchanged or ID mismatch. Version: {refined_schema.get('version')}"
        else: message = f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_validate_object_against_schema():
    global generated_schema_id_global
    if not generated_schema_id_global:
        print_test_result(f"POST /json-schemas/N/A/validate-object (Valid Obj)", False, "Skipped: No schema_id.")
        print_test_result(f"POST /json-schemas/N/A/validate-object (Invalid Obj)", False, "Skipped: No schema_id.")
        print("=" * 30); return

    valid_payload_data = {"json_object": {"name": "Valid Name", "value": 42, "is_active": True}} # Adjust to match generated schema for TestItemForSchema
    test_name_valid = f"POST /json-schemas/{generated_schema_id_global}/validate-object (Valid)"
    print(f"Starting Test: {test_name_valid}")
    success_valid = False; message_valid = ""
    try:
        response = requests.post(f"{BASE_URL}/json-schemas/{generated_schema_id_global}/validate-object", headers=HEADERS, json=valid_payload_data, timeout=10)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("is_valid") is True:
            success_valid = True; message_valid = "Valid object passed."
        else: message_valid = f"Valid object failed or non-200. Status: {response.status_code}. Valid: {response.json().get('is_valid', 'N/A')}"
    except Exception as e: message_valid = f"Error: {e}"
    print_test_result(test_name_valid, success_valid, message_valid)
    time.sleep(0.2)

    invalid_payload_data = {"json_object": {"name": 123, "value": "not-an-integer"}}
    test_name_invalid = f"POST /json-schemas/{generated_schema_id_global}/validate-object (Invalid)"
    print(f"Starting Test: {test_name_invalid}")
    success_invalid = False; message_invalid = ""
    try:
        response = requests.post(f"{BASE_URL}/json-schemas/{generated_schema_id_global}/validate-object", headers=HEADERS, json=invalid_payload_data, timeout=10)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("is_valid") is False and response.json().get("errors"):
            success_invalid = True; message_invalid = f"Invalid object failed with {len(response.json().get('errors'))} errors."
        else: message_invalid = f"Invalid object passed or errors missing. Status: {response.status_code}. Valid: {response.json().get('is_valid', 'N/A')}"
    except Exception as e: message_invalid = f"Error: {e}"
    print_test_result(test_name_invalid, success_invalid, message_invalid)
    print("=" * 30)

def test_approve_schema():
    global generated_schema_id_global, approved_schema_id_for_linking
    test_name = f"PUT /json-schemas/{generated_schema_id_global} (Approve Schema)"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not generated_schema_id_global:
        message = "Skipped: No schema_id provided."
        print_test_result(test_name, False, message); print("=" * 30); return
    
    approval_payload = {"status": "approved_master"}
    try:
        response = requests.put(f"{BASE_URL}/json-schemas/{generated_schema_id_global}", headers=HEADERS, json=approval_payload, timeout=10)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("status") == "approved_master":
            success = True; message = f"Schema {generated_schema_id_global} approved."
            approved_schema_id_for_linking = generated_schema_id_global # Set the ID for linking
        else: message = f"Failed. Status: {response.status_code} or status mismatch."
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)


def test_generate_mock_data():
    global mock_data_prompt_id_global, created_mock_item_ids_global, approved_schema_id_for_linking
    test_name = f"POST /json-schemas/{approved_schema_id_for_linking}/generate-mock-data"
    print(f"Starting Test: {test_name}")
    success = False; message = ""; mock_data_prompt_id_global = None; created_mock_item_ids_global = []
    if not approved_schema_id_for_linking:
        message = "Skipped: No approved_schema_id for mock data generation."
        print_test_result(test_name, False, message); print("=" * 30); return
    payload = {"prompt_text": "Generate 2 simple user profiles with name (string) and age (integer).", "desired_item_count": 2}
    try:
        response = requests.post(f"{BASE_URL}/json-schemas/{approved_schema_id_for_linking}/generate-mock-data", headers=HEADERS, json=payload, timeout=90)
        print_response_summary(response)
        if response.status_code == 201:
            r_json = response.json()
            prompt_details = r_json.get("prompt_details")
            if prompt_details and prompt_details.get("id"):
                mock_data_prompt_id_global = prompt_details["id"]
                message = f"Mock data generation initiated. Prompt ID: {mock_data_prompt_id_global}."
                generated_items = prompt_details.get("generated_items", [])
                if len(generated_items) > 0: success = True; message += f" {len(generated_items)} items returned."
                elif "LLM failed" in r_json.get("message", ""): success = True; message += " LLM generation failed as per message, prompt created."
                else: success = True; message += " Prompt created, but LLM might not have returned items as expected."
                for item in generated_items: created_mock_item_ids_global.append(item["id"])
            else: message = "Response missing prompt details or ID."
        else: message = f"Failed with status {response.status_code}."
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_list_mock_data_prompts(expected_min_count: int = 0):
    test_name = f"GET /mock-data/prompts/ (expecting >={expected_min_count})"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    try:
        response = requests.get(f"{BASE_URL}/mock-data/prompts/", headers=HEADERS, timeout=10)
        print_response_summary(response)
        if response.status_code == 200:
            data = response.json()
            success = isinstance(data, list) and len(data) >= expected_min_count
            message = f"Listed {len(data)} prompts." if success else f"Count mismatch ({len(data)}) or not a list."
        else: message = f"Failed with status {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_get_mock_data_prompt():
    global mock_data_prompt_id_global
    test_name = f"GET /mock-data/prompts/{mock_data_prompt_id_global}"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not mock_data_prompt_id_global: message = "Skipped: No mock_data_prompt_id"; print_test_result(test_name, False, message); print("="*30); return
    try:
        response = requests.get(f"{BASE_URL}/mock-data/prompts/{mock_data_prompt_id_global}", headers=HEADERS, timeout=10)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("id") == mock_data_prompt_id_global:
            success = True; message = f"Prompt {mock_data_prompt_id_global} retrieved."
        else: message = f"Failed. Status: {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_manually_add_mock_item():
    global mock_data_prompt_id_global, created_mock_item_ids_global
    test_name = f"POST /mock-data/prompts/{mock_data_prompt_id_global}/items/"
    print(f"Starting Test: {test_name}")
    success = False; message = ""; item_id = None
    if not mock_data_prompt_id_global: message = "Skipped: No mock_data_prompt_id"; print_test_result(test_name, False, message); print("="*30); return None
    payload = {"item_content": {"manual_field": "manual_value"}}
    try:
        response = requests.post(f"{BASE_URL}/mock-data/prompts/{mock_data_prompt_id_global}/items/", headers=HEADERS, json=payload, timeout=10)
        print_response_summary(response)
        if response.status_code == 201 and response.json().get("id"):
            item_id = response.json().get("id")
            created_mock_item_ids_global.append(item_id)
            success = True; message = f"Manually added item ID: {item_id}."
        else: message = f"Failed. Status: {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)
    return item_id


def test_update_mock_data_item(item_id_to_update: Optional[int]):
    test_name = f"PUT /mock-data/items/{item_id_to_update}"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not item_id_to_update: message = "Skipped: No item_id_to_update"; print_test_result(test_name, False, message); print("="*30); return
    payload = {"item_content": {"manual_field": "updated_value_by_script"}}
    try:
        response = requests.put(f"{BASE_URL}/mock-data/items/{item_id_to_update}", headers=HEADERS, json=payload, timeout=10)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("item_content", {}).get("manual_field") == "updated_value_by_script":
            success = True; message = f"Item {item_id_to_update} updated."
        else: message = f"Failed. Status: {response.status_code} or content mismatch."
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_delete_mock_data_item(item_id_to_delete: Optional[int]):
    test_name = f"DELETE /mock-data/items/{item_id_to_delete}"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not item_id_to_delete: message = "Skipped: No item_id_to_delete"; print_test_result(test_name, False, message); print("="*30); return
    try:
        response = requests.delete(f"{BASE_URL}/mock-data/items/{item_id_to_delete}", headers=HEADERS, timeout=10)
        # print_response_summary(response) # 204 has no content
        if response.status_code == 204:
            success = True; message = f"Item {item_id_to_delete} deleted."
        else: message = f"Failed. Status: {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_delete_mock_data_prompt():
    global mock_data_prompt_id_global
    test_name = f"DELETE /mock-data/prompts/{mock_data_prompt_id_global}"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not mock_data_prompt_id_global: message = "Skipped: No mock_data_prompt_id"; print_test_result(test_name, False, message); print("="*30); return
    try:
        response = requests.delete(f"{BASE_URL}/mock-data/prompts/{mock_data_prompt_id_global}", headers=HEADERS, timeout=10)
        # print_response_summary(response) # 204 has no content
        if response.status_code == 204:
            success = True; message = f"Prompt {mock_data_prompt_id_global} deleted."
        else: message = f"Failed. Status: {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)


def test_create_master_prompt():
    global master_prompt_id_global, approved_schema_id_for_linking
    test_name = "POST /master-prompts/"
    print(f"Starting Test: {test_name}")
    success = False; message = ""; master_prompt_id_global = None
    unique_name = f"TestMasterPrompt_{int(time.time())}"
    payload = {
        "name": unique_name,
        "prompt_content": "Master prompt for {{INPUT_DATA}} with schema context.",
        "target_schema_id": approved_schema_id_for_linking # Use the globally set approved schema ID
    }
    try:
        response = requests.post(f"{BASE_URL}/master-prompts/", headers=HEADERS, json=payload, timeout=10)
        print_response_summary(response)
        if response.status_code == 201 and response.json().get("id"):
            master_prompt_id_global = response.json().get("id")
            success = True; message = f"Master prompt '{unique_name}' created with ID: {master_prompt_id_global}."
        else: message = f"Failed. Status: {response.status_code}, Detail: {response.text[:100]}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)


def test_list_master_prompts(expected_min_count: int = 0):
    test_name = f"GET /master-prompts/ (expecting >={expected_min_count})"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    try:
        response = requests.get(f"{BASE_URL}/master-prompts/", headers=HEADERS, timeout=10)
        print_response_summary(response)
        if response.status_code == 200:
            data = response.json()
            success = isinstance(data, list) and len(data) >= expected_min_count
            message = f"Listed {len(data)} master prompts." if success else f"Count mismatch ({len(data)}) or not list."
        else: message = f"Failed. Status: {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_get_master_prompt():
    global master_prompt_id_global
    test_name = f"GET /master-prompts/{master_prompt_id_global}"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not master_prompt_id_global: message = "Skipped: No master_prompt_id"; print_test_result(test_name, False, message); print("="*30); return
    try:
        response = requests.get(f"{BASE_URL}/master-prompts/{master_prompt_id_global}", headers=HEADERS, timeout=10)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("id") == master_prompt_id_global:
            success = True; message = f"Master prompt {master_prompt_id_global} retrieved."
        else: message = f"Failed. Status: {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_update_master_prompt():
    global master_prompt_id_global
    test_name = f"PUT /master-prompts/{master_prompt_id_global}"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not master_prompt_id_global: message = "Skipped: No master_prompt_id"; print_test_result(test_name, False, message); print("="*30); return
    updated_content = f"Refined master prompt for {{INPUT_DATA}} - update {int(time.time())}"
    payload = {"prompt_content": updated_content}
    try:
        response = requests.put(f"{BASE_URL}/master-prompts/{master_prompt_id_global}", headers=HEADERS, json=payload, timeout=10)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("prompt_content") == updated_content:
            success = True; message = f"Master prompt {master_prompt_id_global} updated."
        else: message = f"Failed. Status: {response.status_code} or content mismatch."
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_refine_master_prompt_with_llm():
    global master_prompt_id_global
    test_name = f"POST /master-prompts/{master_prompt_id_global}/refine-with-llm"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not master_prompt_id_global: message = "Skipped: No master_prompt_id"; print_test_result(test_name, False, message); print("="*30); return
    payload = {"feedback": "Make this prompt even clearer for complex JSON generation."}
    original_content = "" # Could fetch to compare, but for now just check success
    try:
        response = requests.post(f"{BASE_URL}/master-prompts/{master_prompt_id_global}/refine-with-llm", headers=HEADERS, json=payload, timeout=60)
        print_response_summary(response)
        if response.status_code == 200 and response.json().get("id") == master_prompt_id_global:
            success = True; message = f"Master prompt {master_prompt_id_global} refined."
        else: message = f"Failed. Status: {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_list_items_for_prompt(prompt_id: Optional[int], expected_min_item_count: int):
    # Renamed parameter for clarity, ensure it's Optional if prompt_id can be None
    test_name = f"GET /mock-data/prompts/{prompt_id}/items/"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not prompt_id: 
        message = "Skipped: No prompt_id provided for listing items."
        print_test_result(test_name, False, message); print("="*30); return
    try:
        response = requests.get(f"{BASE_URL}/mock-data/prompts/{prompt_id}/items/", headers=HEADERS, timeout=10)
        print_response_summary(response)
        items = response.json()
        if response.status_code == 200 and isinstance(items, list) and len(items) >= expected_min_item_count:
            success = True; message = f"Listed {len(items)} items for prompt {prompt_id} (expected >={expected_min_item_count})."
        else: 
            message = f"Failed. Status: {response.status_code}, Count: {len(items) if isinstance(items, list) else 'N/A'}, Expected >={expected_min_item_count}"
    except Exception as e: 
        message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)


def test_delete_master_prompt():
    global master_prompt_id_global
    test_name = f"DELETE /master-prompts/{master_prompt_id_global}"
    print(f"Starting Test: {test_name}")
    success = False; message = ""
    if not master_prompt_id_global: message = "Skipped: No master_prompt_id"; print_test_result(test_name, False, message); print("="*30); return
    try:
        response = requests.delete(f"{BASE_URL}/master-prompts/{master_prompt_id_global}", headers=HEADERS, timeout=10)
        if response.status_code == 204:
            success = True; message = f"Master prompt {master_prompt_id_global} deleted."
        else: message = f"Failed. Status: {response.status_code}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

# Global for Test Run ID
test_run_id_global: Optional[int] = None

def test_initiate_test_run(): # NO ARGUMENTS HERE
    global test_run_id_global, master_prompt_id_global, mock_data_prompt_id_global, approved_schema_id_for_linking # Access globals
    test_name = "POST /test-runs/ (Initiate Test Run)"
    print(f"Starting Test: {test_name}")
    success = False; message = ""; test_run_id_global = None

    # Use the global variables directly
    if not all([master_prompt_id_global, mock_data_prompt_id_global, approved_schema_id_for_linking]):
        message = "Skipped: Missing prerequisite IDs (master_prompt_id, mock_data_prompt_id, or approved_schema_id)."
        print_test_result(test_name, False, message); print("=" * 30); return

    target_llm_ids_to_test = []
    try:
        models_response = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=10)
        if models_response.status_code == 200:
            models = models_response.json()
            if models: 
                # Take the first model_id or id found, ensure it's a string
                model_id_candidate = models[0].get("model_id", models[0].get("id"))
                if model_id_candidate:
                    target_llm_ids_to_test = [str(model_id_candidate)] 
        if not target_llm_ids_to_test: 
            target_llm_ids_to_test = ["placeholder-model-for-test"]
            print("     Warning: No models fetched or no suitable ID found, using placeholder for target_llm_ids.")
    except Exception as e:
        print(f"     Warning: Could not fetch models for test run: {e}. Using placeholder.")
        target_llm_ids_to_test = ["placeholder-model-for-test"]

    payload = {
        "name": f"Test Run Script {int(time.time())}",
        "master_prompt_id": master_prompt_id_global, # Use global
        "mock_data_prompt_id": mock_data_prompt_id_global, # Use global
        "target_llm_model_ids": target_llm_ids_to_test,
        "master_schema_id": approved_schema_id_for_linking # Use global
    }
    
    try:
        response = requests.post(f"{BASE_URL}/test-runs/", headers=HEADERS, json=payload, timeout=15) 
        print_response_summary(response)
        if response.status_code == 202: # 202 Accepted if using background tasks
            response_data = response.json()
            if response_data.get("id") and response_data.get("status") in ["queued", "pending"]:
                test_run_id_global = response_data.get("id")
                success = True
                message = f"Test run successfully initiated with ID: {test_run_id_global}, status: '{response_data.get('status')}'."
            else:
                message = f"Test run initiation returned 202, but response format unexpected: {response_data}"
        else:
            message = f"Failed to initiate test run. Status: {response.status_code}, Detail: {response.text[:200]}"
    except Exception as e:
        message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_initiate_test_run():
    global test_run_id_global, master_prompt_id_global, mock_data_prompt_id_global, approved_schema_id_for_linking
    test_name = "POST /test-runs/ (Initiate Test Run)"
    print(f"Starting Test: {test_name}")
    success = False; message = ""; test_run_id_global = None

    if not all([master_prompt_id_global, mock_data_prompt_id_global, approved_schema_id_for_linking]):
        message = "Skipped: Missing prerequisite IDs (master_prompt_id, mock_data_prompt_id, or approved_schema_id)."
        print_test_result(test_name, False, message); print("=" * 30); return

    target_llm_ids_to_test = []
    try:
        models_response = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=10)
        if models_response.status_code == 200:
            models = models_response.json()
            if models: target_llm_ids_to_test = [model.get("model_id", model.get("id")) for model in models[:1]] 
        if not target_llm_ids_to_test: target_llm_ids_to_test = ["placeholder-model-for-test"]
    except Exception: target_llm_ids_to_test = ["placeholder-model-for-test"]

    payload = {
        "name": f"Test Run Script {int(time.time())}",
        "master_prompt_id": master_prompt_id_global,
        "mock_data_prompt_id": mock_data_prompt_id_global,
        "target_llm_model_ids": target_llm_ids_to_test,
        "master_schema_id": approved_schema_id_for_linking
    }
    try:
        response = requests.post(f"{BASE_URL}/test-runs/", headers=HEADERS, json=payload, timeout=15) 
        print_response_summary(response)
        if response.status_code == 202:
            r_json = response.json()
            if r_json.get("id") and r_json.get("status") in ["queued", "pending"]: # Check for initial statuses
                test_run_id_global = r_json.get("id")
                success = True; message = f"Test run successfully initiated with ID: {test_run_id_global}, status: '{r_json.get('status')}'."
            else: message = f"Status 202 but response format unexpected: {r_json}"
        else: message = f"Failed. Status: {response.status_code}, Detail: {response.text[:100]}"
    except Exception as e: message = f"Error: {e}"
    print_test_result(test_name, success, message)
    print("=" * 30)

# --- NEW Test Functions for Getting Test Run Info ---
def test_list_test_runs(expected_min_count: int = 0):
    """Tests GET /test-runs/ to list all test runs."""
    test_name = f"GET /test-runs/ (List All, expecting >={expected_min_count})"
    print(f"Starting Test: {test_name}")
    success = False
    message = ""
    
    try:
        response = requests.get(f"{BASE_URL}/test-runs/", headers=HEADERS, timeout=10)
        print_response_summary(response)
        
        if response.status_code == 200:
            response_data = response.json()
            if isinstance(response_data, list):
                if len(response_data) >= expected_min_count:
                    success = True
                    message = f"Successfully listed {len(response_data)} test runs (expected at least {expected_min_count})."
                    if len(response_data) > 0:
                        first_run = response_data[0]
                        if "id" in first_run and "status" in first_run and "results" in first_run and isinstance(first_run["results"], list):
                            message += f" First run (ID: {first_run['id']}) seems well-formed with {len(first_run['results'])} results."
                        else:
                            message += " First run item structure seems incomplete."
                else:
                    message = f"Listed {len(response_data)} test runs, but expected at least {expected_min_count}."
            else:
                message = "Response is not a list as expected."
        else:
            message = f"Expected 200 OK, got {response.status_code}."
            
    except requests.exceptions.RequestException as e:
        message = f"Connection Error: {e}"
    except Exception as e:
        message = f"An unexpected error occurred: {e}"
        
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_get_specific_test_run(run_id_to_get: Optional[int]):
    """Tests GET /test-runs/{run_id}"""
    test_name = f"GET /test-runs/{run_id_to_get}"
    print(f"Starting Test: {test_name}")
    success = False
    message = ""

    if not run_id_to_get:
        message = "Skipped: No run_id_to_get provided."
        print_test_result(test_name, False, message)
        print("=" * 30)
        return

    # Wait a moment for background tasks to potentially process
    print(f"     Pausing for a few seconds to allow background task for TestRun ID {run_id_to_get} to progress...")
    time.sleep(10) # Adjust as needed, or implement polling for "completed" status

    try:
        response = requests.get(f"{BASE_URL}/test-runs/{run_id_to_get}", headers=HEADERS, timeout=10)
        print_response_summary(response)
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("id") == run_id_to_get:
                success = True
                message = f"Successfully retrieved TestRun ID: {run_id_to_get}. Status: {response_data.get('status')}."
                if "results" in response_data and isinstance(response_data["results"], list):
                    message += f" Found {len(response_data['results'])} results."
                    # Further checks on results content can be added here if specific outcomes are expected
                else:
                    message += " 'results' field missing or not a list."
            else:
                message = "Response ID does not match requested run_id."
        elif response.status_code == 404:
            message = f"TestRun ID: {run_id_to_get} not found (404), which might be unexpected."
        else:
            message = f"Expected 200 OK, got {response.status_code}."
            
    except requests.exceptions.RequestException as e:
        message = f"Connection Error: {e}"
    except Exception as e:
        message = f"An unexpected error occurred: {e}"
        
    print_test_result(test_name, success, message)
    print("=" * 30)

def test_get_test_run_summary(run_id_to_get: Optional[int]):
    """Tests GET /test-runs/{run_id}/summary-by-llm"""
    test_name = f"GET /test-runs/{run_id_to_get}/summary-by-llm"
    print(f"Starting Test: {test_name}")
    success = False
    message = ""

    if not run_id_to_get:
        message = "Skipped: No run_id_to_get provided for summary."
        print_test_result(test_name, False, message)
        print("=" * 30)
        return

    # Wait a bit longer to ensure background tasks for test result creation have progressed
    print(f"     Pausing for a significant duration (e.g., 15-20s) to allow TestRun ID {run_id_to_get} to complete more results...")
    time.sleep(20) # Adjust this based on how long your actual LLM calls take.

    try:
        response = requests.get(f"{BASE_URL}/test-runs/{run_id_to_get}/summary-by-llm", headers=HEADERS, timeout=15)
        print_response_summary(response)
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("test_run_id") == run_id_to_get and "llm_summaries" in response_data:
                success = True
                message = f"Successfully retrieved summary for TestRun ID: {run_id_to_get}. Found {len(response_data['llm_summaries'])} LLM summaries."
                if len(response_data['llm_summaries']) > 0:
                    first_summary = response_data['llm_summaries'][0]
                    if "target_llm_model_id" in first_summary and "total_tests" in first_summary:
                        message += " First summary item seems well-formed."
                    else:
                        success = False # Or just a warning in message
                        message += " First summary item structure incomplete."
                elif response_data.get("overall_total_tests", -1) == 0 : # Check if it's an empty summary for a run with no results yet
                     message += " Summary indicates no tests/results processed yet, which might be as expected depending on timing."
                     # success can remain true if the structure is correct for an empty summary
                else:
                    success = False # If not empty, but summaries list is empty without overall_total_tests being 0
                    message += " LLM summaries list is empty but overall_total_tests is not 0 or was not present."

            else:
                message = "Response format unexpected or test_run_id mismatch."
        elif response.status_code == 404:
            message = f"TestRun ID: {run_id_to_get} not found (404), which might be unexpected if test initiation passed."
        else:
            message = f"Expected 200 OK, got {response.status_code}."
            
    except requests.exceptions.RequestException as e:
        message = f"Connection Error: {e}"
    except Exception as e:
        message = f"An unexpected error occurred: {e}"
        
    print_test_result(test_name, success, message)
    print("=" * 30)

# --- Main Execution ---
if __name__ == "__main__":
    if not backup_and_reset_database(DATABASE_FILE_PATH):
        exit() 

    print("IMPORTANT: Database has been reset (or prepared for initial creation).")
    print("1. Please (RE)START your FastAPI server now.")
    print("   This ensures it connects to a fresh database and creates all tables.")
    print("2. Also, ensure your LiteLLM service is running and configured correctly,")
    print("   and 'DEFAULT_ASSISTANT_MODEL_ID' in '.env' points to a capable model.")
    input("\n>>> Press Enter to continue with API tests once the FastAPI server is ready... ")

    print(f"\nStarting API tests against {BASE_URL}...\n")
    test_results = {"passed": 0, "failed": 0, "details": []} # Reset results

    # --- Phase 1 & Prerequisite Tests ---
    print("\n--- Running Basic and Phase 1 Schema Tests ---")
    test_root(); time.sleep(0.1)
    test_get_models(); time.sleep(0.1)
    
    test_list_json_examples(0); time.sleep(0.1) # Expect 0 before creation
    test_create_json_example(); time.sleep(0.1) # Sets created_example_id_global
    if created_example_id_global:
        test_list_json_examples(1); time.sleep(0.1) # Expect 1 after creation
    
    test_list_json_schemas(0); time.sleep(0.1) # Expect 0 before generation
    if created_example_id_global:
        test_generate_schema(); time.sleep(0.1) # Sets generated_schema_id_global
    
    if generated_schema_id_global:
        test_list_json_schemas(1); time.sleep(0.1) # Expect 1 after generation
        test_get_json_schema(); time.sleep(0.1)
        test_update_json_schema(); time.sleep(0.1)
        test_refine_json_schema_with_llm(); time.sleep(0.1)
        test_validate_object_against_schema(); time.sleep(0.1)
        test_approve_schema(); time.sleep(0.1) # Sets approved_schema_id_for_linking
    else:
        # Log skips for dependent tests
        for test_name_format in ["List Schemas (after gen)", "Get Schema {}", "Update Schema {}", "Refine Schema {}", "Validate Schema {}", "Approve Schema {}"]:
             print_test_result(test_name_format.format("N/A"), False, "Skipped: Prerequisite schema_id not available.")


    # --- Phase 2: Mock Data Tests ---
    print("\n--- Running Phase 2: Mock Data Endpoint Tests ---")
    if approved_schema_id_for_linking:
        test_generate_mock_data(); time.sleep(0.1) # Sets mock_data_prompt_id_global and created_mock_item_ids_global
        if mock_data_prompt_id_global:
            test_list_mock_data_prompts(1); time.sleep(0.1)
            test_get_mock_data_prompt(); time.sleep(0.1)
            test_list_items_for_prompt(mock_data_prompt_id_global, len(created_mock_item_ids_global)); time.sleep(0.1)
            
            manually_added_item_id = test_manually_add_mock_item(); time.sleep(0.1)
            if manually_added_item_id:
                test_update_mock_data_item(manually_added_item_id); time.sleep(0.1)
                test_delete_mock_data_item(manually_added_item_id); time.sleep(0.1)
            
            if created_mock_item_ids_global: # Delete one of the LLM generated items
                item_to_delete = created_mock_item_ids_global.pop(0)
                test_delete_mock_data_item(item_to_delete); time.sleep(0.1)
            
            #test_delete_mock_data_prompt(); time.sleep(0.1) # Deletes the prompt and remaining items
            test_list_mock_data_prompts(0); time.sleep(0.1)
        else:
            for test_name in ["List Mock Prompts", "Get Mock Prompt", "Delete Mock Prompt", "List Items for Prompt", "Manual Add Item"]:
                 print_test_result(f"Mock Data Test ({test_name})", False, "Skipped: Prerequisite mock_data_prompt_id not available.")
    else:
        for test_name in ["Generate Mock Data", "List Mock Prompts", "Get Mock Prompt", "Delete Mock Prompt", "List Items for Prompt", "Manual Add Item"]:
             print_test_result(f"Mock Data Test ({test_name})", False, "Skipped: Prerequisite approved_schema_id not available.")

    # --- Phase 3: Master Prompt Tests ---
    print("\n--- Running Phase 3: Master Prompt Endpoint Tests ---")
    test_list_master_prompts(0); time.sleep(0.1)
    test_create_master_prompt(); time.sleep(0.1) # Uses approved_schema_id_for_linking, sets master_prompt_id_global

    if master_prompt_id_global:
        test_list_master_prompts(1); time.sleep(0.1)
        test_get_master_prompt(); time.sleep(0.1)
        test_update_master_prompt(); time.sleep(0.1)
        test_refine_master_prompt_with_llm(); time.sleep(0.1)
        #test_delete_master_prompt(); time.sleep(0.1)
        test_list_master_prompts(0)
    else:
        for test_name_format in ["List Master Prompts (after create)", "Get Master Prompt {}", "Update Master Prompt {}", "Refine Master Prompt {}", "Delete Master Prompt {}"]:
            print_test_result(test_name_format.format("N/A"), False, "Skipped: Prerequisite master_prompt_id not available.")
    
    # --- Phase 4: Test Run Initiation ---
    print("\n--- Running Phase 4: Test Run Initiation Test ---")
    if master_prompt_id_global and mock_data_prompt_id_global and approved_schema_id_for_linking:
        test_initiate_test_run() # Call without arguments
        
        if test_run_id_global:
            print(f"    To check status later, query: GET /test-runs/{test_run_id_global}")
            test_list_test_runs(expected_min_count=1) # Test listing after creation
            time.sleep(0.1)
            test_get_specific_test_run(test_run_id_global) # Test getting the specific run
        else:
            # Update skip messages for dependent tests
            print_test_result("GET /test-runs/ (after initiation)", False, "Skipped: Test run initiation failed or returned no ID.")
            print_test_result(f"GET /test-runs/{{run_id}}", False, "Skipped: Test run initiation failed or returned no ID.")
    else:
        message = "Skipped Test Run Initiation: Missing prerequisite IDs (master_prompt, mock_data_prompt, or approved_schema)."
        print_test_result("POST /test-runs/", False, message)
        print_test_result("GET /test-runs/ (after initiation)", False, message)
        print_test_result(f"GET /test-runs/{{run_id}}", False, message)

    # --- Phase 4: Test Run Tests ---
    print("\n--- Running Phase 4: Test Run Endpoint Tests ---")
    
    # Test listing test runs (should be 0 initially in a fresh DB)
    test_list_test_runs(expected_min_count=0)
    time.sleep(0.1)

    if master_prompt_id_global and mock_data_prompt_id_global and approved_schema_id_for_linking:
        test_initiate_test_run() # Sets test_run_id_global
        
        if test_run_id_global:
            test_list_test_runs(expected_min_count=1)
            time.sleep(0.1)
            test_get_specific_test_run(test_run_id_global) # Fetches run, results might be populating
            time.sleep(0.1) # Give a moment before fetching summary
            test_get_test_run_summary(test_run_id_global) 
        else:
            print_test_result("GET /test-runs/ (after initiation)", False, "Skipped: Test run initiation failed.")
            print_test_result(f"GET /test-runs/{{run_id}}", False, "Skipped: Test run initiation failed.")
    else:
            for test_name_format in [
                "GET /test-runs/ (after initiation)", 
                "GET /test-runs/{}", 
                "GET /test-runs/{}/summary-by-llm" # Add new test to skip logic
            ]:
                print_test_result(test_name_format.format("N/A"), False, "Skipped: Test run initiation failed or returned no ID.")

    # Clean up master prompt if it was created
    if master_prompt_id_global:
        test_delete_master_prompt(); time.sleep(0.1)
        test_delete_mock_data_prompt(); time.sleep(0.1)

    # --- Final Test Summary ---
    print("\n--- Test Summary ---")
    for result in test_results["details"]:
        print(f"Test: {result['name']} ... {result['status']}")
        if result['message'] and result['status'] != "PASS": 
             print(f"     Message: {result['message']}")
    print(f"Total Passed: {test_results['passed']}")
    print(f"Total Failed (or Skipped): {test_results['failed']}")
    print("--------------------\n")
    print("API tests completed.")