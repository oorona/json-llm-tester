# LLM JSON Generation Evaluator

## Overview

The LLM JSON Generation Evaluator is a web application designed to address the challenge of inconsistent JSON output from Large Language Models (LLMs). It provides a comprehensive suite of tools to help users craft effective prompts, test LLMs against various scenarios, and rigorously evaluate their ability to generate accurate and schema-compliant JSON. The core of this project revolves around leveraging AI (specifically, a user-selected "assistant LLM") to streamline and enhance the process of defining, testing, and refining JSON generation tasks.

## How It Works

The application guides users through a structured, multi-phase process, leveraging a combination of user input, frontend interactions, backend API calls, and LLM-powered assistance:

**Phase 0: Initial Setup & Assistant LLM Selection**
1.  **Welcome & Model Loading:** The user accesses the web application (React SPA). The frontend fetches a list of available LLM models from the backend (`/models` endpoint). The backend, in turn, queries the configured LLM Service Proxy (e.g., LiteLLM) for this list.
2.  **Assistant LLM Choice:** The user selects one LLM from the fetched list to act as the "assistant LLM". This selection is stored in the frontend's state and used for subsequent AI-assisted tasks. This assistant LLM is responsible for schema generation, mock data creation, and master prompt refinement.

**Phase 1: Define Target JSON Structure & Schema (Iterative)**
1.  **JSON Example Submission:** The user provides an example of the target JSON structure (e.g., by pasting it into a text area in the `JsonExampleInput` component).
2.  **Initial Schema Generation Request:** The frontend sends this example JSON to the backend (`POST /json-examples/` to create the example, then `POST /json-examples/{example_id}/generate-schema`).
3.  **AI Schema Generation:** The backend uses the selected assistant LLM to generate an initial JSON schema based on the provided example. The `llm_service.py` handles the call to the LLM Service Proxy. The generated schema is saved in the database.
4.  **Schema Review & Refinement Loop (`SchemaDisplayAndActions` component):**
    * The UI displays the user's example and the LLM-generated schema.
    * **Direct Edit:** The user can manually edit the schema text. Changes can be saved via `PUT /json-schemas/{schema_id}`.
    * **LLM-Assisted Refinement:** The user provides textual feedback. The frontend sends this feedback, the current schema, and optionally the original example to the backend (`POST /json-schemas/{schema_id}/refine-with-llm`). The backend then uses the assistant LLM to generate a revised schema.
    * **Test Schema:** The user can paste a sample JSON object to validate it against the current schema (`POST /json-schemas/{schema_id}/validate-object`). The backend performs this validation.
5.  **Approve Schema:** Once satisfied, the user approves the schema. This typically involves updating its status in the database (e.g., to "approved\_master") via `PUT /json-schemas/{schema_id}`. This "master schema" is crucial for later validation.

**Phase 2: Generate and Refine Mock Input Data (Iterative)**
1.  **Prompt for Mock Data:** In the `MockDataGenerator` component, the user writes a textual prompt describing the desired mock data scenarios (e.g., "Generate 5 realistic user profiles") and specifies the number of items.
2.  **AI Mock Data Generation Request:** The frontend sends this prompt and quantity to the backend, targeting an approved master schema (`POST /json-schemas/{schema_id}/generate-mock-data`).
3.  **AI Generates Mock Data:** The backend uses the assistant LLM to generate the mock data items based on the user's prompt and the context of the master schema. These items are stored in the database, linked to the generation prompt.
4.  **Review & Curate (`MockDataManagement` and `MockDataItem` components):**
    * Generated items are displayed. Users can edit (`PUT /mock-data/items/{item_id}`), add new items manually (`POST /mock-data/prompts/{prompt_id}/items/`), or delete items (`DELETE /mock-data/items/{item_id}` or `DELETE /mock-data/prompts/{prompt_id}` for the whole set).
5.  **Confirm Mock Data:** The user finalizes the list of mock input data.

**Phase 3: Craft Master Prompt (Iterative & LLM-Assisted)**
1.  **Initial Prompt Creation (`MasterPromptEditor` component):** The user writes an initial "master prompt" that will instruct target LLMs. This prompt must include a placeholder (e.g., `{{INPUT_DATA}}`) for injecting mock data items. The prompt is saved via `POST /master-prompts/` or updated via `PUT /master-prompts/{id}`.
2.  **LLM-Assisted Prompt Refinement:**
    * The user can provide feedback or ask the assistant LLM to help improve the master prompt.
    * The frontend sends the current prompt, feedback, and optionally context (like the master schema) to the backend (`POST /master-prompts/{id}/refine-with-llm`).
    * The backend uses the assistant LLM to suggest revisions.
3.  **Save Master Prompt:** The user finalizes and saves the master prompt.

**Phase 4: Select Models & Run Tests (`TestRunner` component)**
1.  **Select Target LLMs:** The user selects one or more LLMs from the available list (fetched in Phase 0) to be evaluated.
2.  **Initiate Test Run:** The user provides a name for the test run and confirms selections (master prompt, mock data set, target LLMs, master schema). The frontend sends this configuration to the backend (`POST /test-runs/`).
3.  **Backend Test Execution (Async):**
    * The backend creates a `TestRun` record in the database and queues background tasks to perform the actual testing. This prevents HTTP timeouts.
    * For each selected target LLM and for each mock input item:
        * The mock data item is injected into the master prompt.
        * The finalized prompt is sent to the current target LLM via the LLM Service Proxy (`llm_service.call_llm_chat_completions`).
        * The LLM's raw JSON output is received.
        * The output is parsed, and its validity against the master schema is checked.
        * Results (input, output, parse status, schema compliance, errors, execution time, token usage) are stored in the database as `TestResult` records linked to the `TestRun`.

**Phase 5: View & Analyze Results (`TestRunSelector` and `ResultsDashboard` components)**
1.  **Select Test Run:** The user selects a completed (or in-progress) test run from a list (`GET /test-runs/`).
2.  **Display Results:**
    * The frontend fetches detailed results for the selected test run (`GET /test-runs/{id}`) and summary statistics (`GET /test-runs/{id}/summary-by-llm`).
    * **Summary Dashboard:** Shows aggregated scores, schema compliance percentages, average execution times, etc., for each tested LLM, often using tables and charts (`SummaryTable`, charts are planned).
    * **Detailed Drill-Down:** Users can view a table (`DetailedResultsTable`) listing individual test cases: the mock input, raw LLM output, parse status, schema compliance status, and specific validation errors if any.

Throughout the process, the FastAPI backend handles API requests, interacts with the SQLite database for persistence, and manages LLM communications. The React frontend provides the user interface and manages client-side state.

## Core AI-Powered Features

This application utilizes an "assistant LLM" (selected by the user from a list of available models via an LLM Service Proxy) to power several key phases of the workflow:

1.  **AI-Assisted JSON Schema Generation & Refinement:**
    * **Initial Schema Generation:** Users provide an example JSON object, and the assistant LLM generates an initial JSON schema based on this example.
    * **Iterative Schema Refinement:** Users can provide textual feedback on the generated schema. The system sends this feedback, along with the current schema and original example, to the assistant LLM to produce a revised and improved schema. This iterative loop allows for precise schema definition guided by AI.

2.  **AI-Driven Mock Data Generation:**
    * Users write a textual prompt describing the desired mock data scenarios (e.g., "Generate 10 realistic user profiles with diverse names and addresses").
    * The assistant LLM uses this prompt, along with the approved master JSON schema for context, to generate a specified number of mock data items. This ensures that test data is relevant and varied.

3.  **AI-Assisted Master Prompt Engineering:**
    * Users can craft an initial "master prompt" intended for the target LLMs that will be evaluated.
    * The assistant LLM can be engaged to help generate or iteratively refine this master prompt. It can take into account the target JSON schema or example JSON to create more effective prompts for structured data generation.

4.  **LLM Performance Evaluation:**
    * The primary goal is to evaluate how well different "target LLMs" (also selected by the user) can generate JSON according to the master prompt and schema.
    * The system orchestrates test runs where each target LLM processes each mock data item injected into the master prompt.
    * Outputs are then validated against the master schema for correctness (valid JSON structure, data types, mandatory fields).

## Key Technologies

* **Backend:** Python, FastAPI
* **Frontend:** React (with Vite)
* **Database:** SQLite (initial), with option for PostgreSQL
* **LLM Interaction:** Via an external LLM Service Proxy (OpenAI-compatible API)
* **Styling:** Tailwind CSS
* **Deployment:** Docker (planned)

This project aims to provide a robust platform for systematically improving and evaluating the reliability of LLMs in generating structured JSON data.