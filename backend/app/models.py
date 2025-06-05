# backend/app/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- LLM Service Models ---
class LLMModel(BaseModel):
    """
    Pydantic model for representing an LLM model's information.
    """
    model_id: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True # Useful if this model might ever be created from an ORM object


class ChatMessageInput(BaseModel):
    """
    Pydantic model for a single message in a chat completion request.
    """
    role: str # Typically "user", "assistant", or "system"
    content: str


class ChatCompletionRequest(BaseModel):
    """
    Pydantic model for the request body of a chat completion call.
    """
    model_id: str
    messages: List[ChatMessageInput]
    temperature: float = 0.7
    max_tokens: int = 1024


# --- Pydantic Models for JSON Examples API ---

class JsonExampleCreate(BaseModel):
    """
    Pydantic model for creating a new JSON example.
    User provides the content and an optional description.
    """
    content: Dict[Any, Any] = Field(..., example={"key": "value", "items": [1, 2, 3]})
    description: Optional[str] = Field(None, example="A sample user profile structure.")


class JsonExampleResponse(BaseModel):
    """
    Pydantic model for the response when a JSON example is retrieved or created.
    """
    id: int
    content: Dict[Any, Any]
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Enables creating this model from an ORM object (e.g., db_models.JsonExample)


# --- Pydantic Models for JSON Schemas API (Placeholder for future development) ---

class JsonSchemaCreate(BaseModel):
    """
    Pydantic model for creating a new JSON schema.
    """
    name: Optional[str] = Field(None, example="UserProfileSchema_Generated_v1")
    schema_content: Dict[Any, Any] # The actual JSON schema
    json_example_id: Optional[int] = None # Link to the source example if any
    status: str = "draft" # Default status

class JsonSchemaResponse(BaseModel):
    """
    Pydantic model for the response when a JSON schema is retrieved or created.
    """
    id: int
    name: Optional[str] = None
    schema_content: Dict[Any, Any]
    version: int
    status: str
    json_example_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    # Optionally include the source example in the response:
    # source_example: Optional[JsonExampleResponse] = None # If you want to nest, ensure your DB query populates this

    class Config:
        from_attributes = True


class JsonSchemaUpdate(BaseModel):
    """
    Pydantic model for updating an existing JSON schema.
    Allows updating name, schema_content, and status.
    All fields are optional, so only provided fields will be updated.
    """
    name: Optional[str] = Field(None, example="UserProfileSchema_Updated_v1")
    schema_content: Optional[Dict[Any, Any]] = Field(None, example={"type": "object", "properties": {"username": {"type": "string", "description": "Updated field"}}})
    status: Optional[str] = Field(None, example="reviewed") # e.g., "draft", "reviewed", "approved_master"
    version: Optional[int] = None # Optionally allow version bumping manually, or handle automatically

    class Config:
        from_attributes = True # Good practice, though mainly for response models

class JsonSchemaRefineRequest(BaseModel):
    """
    Pydantic model for the request to refine a JSON schema using LLM assistance.
    User provides textual feedback.
    """
    feedback: str = Field(..., example="Make the 'email' field a required property and ensure it follows a standard email format. Add a 'last_login' field as an optional ISO datetime string.")
    # Optionally, allow user to suggest a new name or other metadata for the refined version
    # new_name: Optional[str] = None


class JsonObjectToValidate(BaseModel):
    """
    Pydantic model for the JSON object that the user wants to validate against a schema.
    """
    json_object: Dict[Any, Any] = Field(..., example={"name": "Test User", "age": 30, "email": "test@example.com"})

class SchemaValidationErrorDetail(BaseModel):
    """
    Pydantic model for a single validation error detail.
    """
    message: str
    path: List[str] # Path to the error in the JSON object (e.g., ["user", "email"])
    validator: str # Which validator failed (e.g., "type", "required")
    # schema_path: List[str] # Path in the schema that failed validation

class SchemaValidationResponse(BaseModel):
    """
    Pydantic model for the response of a schema validation request.
    """
    is_valid: bool
    errors: Optional[List[SchemaValidationErrorDetail]] = None # List of errors if not valid


class MockDataItemBase(BaseModel):
    item_content: Dict[Any, Any] = Field(..., example={"name": "Mock User", "email": "mock@example.com", "bio": "A mock bio."})

class MockDataItemCreate(MockDataItemBase):
    """ For creating a new mock data item manually. """
    pass

class MockDataItemUpdate(MockDataItemBase):
    """ For updating a mock data item. Content is required. """
    pass

class MockDataItemResponse(MockDataItemBase):
    id: int
    prompt_id: int # Which generation prompt/context this item belongs to
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MockDataPromptRequest(BaseModel):
    """ Request to generate mock data for a schema. """
    prompt_text: str = Field(..., example="Generate 5 realistic user profiles with name, email, and a short bio.")
    desired_item_count: int = Field(..., gt=0, example=5) # gt=0 means greater than 0

class MockDataPromptResponse(BaseModel):
    """ Response for a mock data prompt, including its generated items. """
    id: int
    prompt_text: str
    desired_item_count: int
    target_schema_id: int
    created_at: datetime
    updated_at: datetime
    generated_items: List[MockDataItemResponse] = [] # Eagerly load and show items

    class Config:
        from_attributes = True

class MockDataGenerationInitiatedResponse(BaseModel):
    """ Response after initiating mock data generation. """
    prompt_details: MockDataPromptResponse
    message: Optional[str] = None    


class MockDataPromptBase(BaseModel):
    prompt_text: str = Field(..., example="Generate 5 realistic user profiles with name, email, and a short bio.")
    desired_item_count: int = Field(..., gt=0, example=5) # gt=0 means greater than 0

class MockDataPromptCreate(MockDataPromptBase):
    # target_schema_id will be taken from path parameter in the endpoint
    pass

class MockDataGenerationResponse(BaseModel): # Specific response after generation
    prompt_details: MockDataPromptResponse
    # message: Optional[str] = None # Could add a message like "X items generated"


class MasterPromptBase(BaseModel):
    name: str = Field(..., example="ProductJSONGeneration_v1")
    prompt_content: str = Field(..., example="Generate a JSON object for a product using the following input data: {{INPUT_DATA}}. The output must conform to the predefined product schema.")
    target_schema_id: Optional[int] = Field(None, description="ID of the target JSON schema this prompt is designed for.")

class MasterPromptCreate(MasterPromptBase):
    pass

class MasterPromptUpdate(BaseModel): # For partial updates
    name: Optional[str] = None
    prompt_content: Optional[str] = None
    target_schema_id: Optional[int] = None


class MasterPromptResponse(MasterPromptBase):
    id: int
    created_at: datetime
    updated_at: datetime
    target_schema: Optional[JsonSchemaResponse] = None 

    class Config:
        from_attributes = True

class MasterPromptRefineRequest(BaseModel):
    """
    Pydantic model for the request to refine a Master Prompt using LLM assistance.
    User provides textual feedback/instructions.
    """
    feedback: str = Field(..., example="Make the prompt more explicit about handling missing fields in the input data. Ensure it asks for a single JSON object as output.")
  

class TestRunCreate(BaseModel):
    """
    Pydantic model for creating a new test run.
    """
    name: Optional[str] = Field(None, example="My First LLM Comparison Test")
    master_prompt_id: int = Field(..., example=1)
    mock_data_prompt_id: int = Field(..., example=1, description="ID of the MockDataPrompt defining the set of mock inputs.")
    target_llm_model_ids: List[str] = Field(..., min_length=1, example=["gpt-4.1-nano", "geminiflash"])
    master_schema_id: int = Field(..., example=1, description="ID of the JsonSchema to validate results against.")

class TestResultBase(BaseModel):
    target_llm_model_id: str
    mock_input_data_used: Dict[Any, Any]
    llm_raw_output: Optional[str] = None
    parse_status: Optional[bool] = None
    schema_compliance_status: Optional[str] = None # "Pass", "Fail"
    validation_errors: Optional[List[Dict[Any, Any]]] = None # Simplified from SchemaValidationErrorDetail for storage/retrieval
    execution_time_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    error_message: Optional[str] = None

class TestResultResponse(TestResultBase):
    id: int
    test_run_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class TestRunResponse(BaseModel):
    """
    Pydantic model for the response when a test run is retrieved or created.
    """
    id: int
    name: Optional[str] = None
    master_prompt_id: int
    mock_data_prompt_id: int
    target_llm_model_ids: List[str]
    master_schema_id: int
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: List[TestResultResponse] = [] # Optionally include results

    class Config:
        from_attributes = True

class LLMRunSummary(BaseModel):
    """
    Summary statistics for a specific LLM within a test run.
    """
    target_llm_model_id: str
    total_tests: int
    successful_parses: int # Count of outputs that were valid JSON
    schema_compliant_tests: int
    schema_compliance_percentage: float
    average_execution_time_ms: Optional[float] = None
    total_tokens_used: Optional[int] = None # Sum of tokens if available
    # Further breakdown of errors could be added here if needed

class TestRunOverallSummaryResponse(BaseModel):
    """
    Overall summary for a test run, including per-LLM breakdowns.
    """
    test_run_id: int
    test_run_name: Optional[str] = None
    overall_total_tests: int # Sum of total_tests across all LLMs
    llm_summaries: List[LLMRunSummary]