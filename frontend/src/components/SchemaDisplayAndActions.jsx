// frontend/src/components/SchemaDisplayAndActions.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = '';

const SchemaDisplayAndActions = ({ schema, onSchemaUpdated, selectedAssistantLlm }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refinementFeedback, setRefinementFeedback] = useState('');
  const [validationObject, setValidationObject] = useState('');
  const [validationResult, setValidationResult] = useState(null);
  const [editableSchemaContent, setEditableSchemaContent] = useState('');

  useEffect(() => {
    if (schema && schema.schema_content) {
      setEditableSchemaContent(JSON.stringify(schema.schema_content, null, 2));
    } else {
      setEditableSchemaContent('');
    }
    setValidationResult(null); // Clear previous validation result when schema changes
  }, [schema]);

  if (!schema) {
    return <p className="text-center text-gray-400">No schema selected or generated yet.</p>;
  }

  const handleRefinementFeedbackChange = (e) => setRefinementFeedback(e.target.value);
  const handleValidationObjectChange = (e) => setValidationObject(e.target.value);
  const handleEditableSchemaChange = (e) => setEditableSchemaContent(e.target.value);

  const prettyPrintJson = (json) => {
     if (json === null || json === undefined) return '';
     try { return JSON.stringify(json, null, 2); } 
     catch (e) { return "Error pretty-printing JSON."; }
  };

  const handleLlmRefine = async () => {
    if (!selectedAssistantLlm) {
      setError("Please select an Assistant LLM for refinement.");
      return;
    }
    if (!refinementFeedback.trim()) {
      setError("Please provide feedback for refinement.");
      return;
    }
    setIsLoading(true); setError(null);
    try {
      const url = `${API_BASE_URL}/json-schemas/${schema.id}/refine-with-llm`;
      console.log(`Attempting to handleLlmRefine for schema.id: ${schema.id} with URL: ${url}`);
      const response = await axios.post(url, { feedback: refinementFeedback });
      onSchemaUpdated(response.data); // Notify parent of the update
      setRefinementFeedback(''); // Clear input
    } catch (err) {
      console.error("Error refining schema with LLM:", err);
      setError(err.response?.data?.detail || err.message || "Failed to refine schema.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleValidateObject = async () => {
    let objectToValidate;
    try {
      objectToValidate = JSON.parse(validationObject);
    } catch (e) {
      setValidationResult({ is_valid: false, errors: [{ message: "Invalid JSON for validation object.", path: [], validator: "input_format" }] });
      return;
    }
    setIsLoading(true); setError(null); setValidationResult(null);
    try {
      const url = `${API_BASE_URL}/json-schemas/${schema.id}/validate-object`;
      console.log(`Attempting to handleValidateObject for schema.id: ${schema.id} with URL: ${url}`);

      const response = await axios.post(url, { json_object: objectToValidate });
      setValidationResult(response.data);
    } catch (err) {
      console.error("Error validating object:", err);
      setError(err.response?.data?.detail || err.message || "Failed to validate object.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveSchema = async () => {
    setIsLoading(true); setError(null);
    try {
      const url = `${API_BASE_URL}/json-schemas/${schema.id}`;
      console.log(`Attempting to handleApproveSchema for schema.id: ${schema.id} with URL: ${url}`);
      const response = await axios.put(url, { status: "approved_master" });

      onSchemaUpdated(response.data);
    } catch (err) {
      console.error("Error approving schema:", err);
      setError(err.response?.data?.detail || err.message || "Failed to approve schema.");
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleDirectUpdateSchema = async () => {
     let parsedSchemaContent;
     try {
         parsedSchemaContent = JSON.parse(editableSchemaContent);
     } catch (e) {
         setError("Schema content is not valid JSON. Please correct it before saving.");
         return;
     }
     setIsLoading(true); setError(null);
     try {
         const url = `${API_BASE_URL}/json-schemas/${schema.id}`;
         console.log(`Attempting to handleDirectUpdateSchema for schema.id: ${schema.id} with URL: ${url}`);
         // You might want to allow updating name/version via UI fields too
         const payload = { schema_content: parsedSchemaContent };
         const response = await axios.put(url, payload);
         onSchemaUpdated(response.data); // Notify parent
     } catch (err) {
         console.error("Error updating schema directly:", err);
         setError(err.response?.data?.detail || err.message || "Failed to update schema.");
     } finally {
         setIsLoading(false);
     }
  };

  return (
    <div className="mt-6 p-6 bg-gray-800 rounded-lg shadow-xl">
      <h3 className="text-xl font-semibold text-green-300 mb-3">
        Current Schema (ID: {schema.id}, Version: {schema.version}, Status: <span className={`font-bold ${schema.status === 'approved_master' ? 'text-green-400' : 'text-yellow-400'}`}>{schema.status}</span>)
      </h3>
      
      {/* Direct Schema Edit */}
      <div className="mb-4">
         <label htmlFor="schemaEdit" className="block text-sm font-medium text-gray-300 mb-1">Edit Schema Content:</label>
         <textarea
             id="schemaEdit"
             rows="15"
             value={editableSchemaContent}
             onChange={handleEditableSchemaChange}
             className="w-full p-2 bg-gray-900 border border-gray-700 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm text-white"
         />
         <button
             onClick={handleDirectUpdateSchema}
             disabled={isLoading}
             className="mt-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-md disabled:opacity-50"
         >
             Save Schema Changes
         </button>
      </div>
      <hr className="my-6 border-gray-700" />

      {/* LLM Refinement */}
      <div className="mb-4">
        <h4 className="text-lg text-blue-300 mb-2">Refine with Assistant LLM</h4>
        <textarea
          rows="3"
          value={refinementFeedback}
          onChange={handleRefinementFeedbackChange}
          className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 text-white"
          placeholder="e.g., Make 'email' required, add 'phone_number' (optional string)."
        />
        <button
          onClick={handleLlmRefine}
          disabled={isLoading || !refinementFeedback.trim() || !selectedAssistantLlm}
          className="mt-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
          title={!selectedAssistantLlm ? "Select Assistant LLM first" : ""}
        >
          Refine Schema with LLM
        </button>
      </div>
      <hr className="my-6 border-gray-700" />

      {/* Test Schema Validation */}
      <div className="mb-4">
        <h4 className="text-lg text-blue-300 mb-2">Test Schema with JSON Object</h4>
        <textarea
          rows="5"
          value={validationObject}
          onChange={handleValidationObjectChange}
          className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm text-white"
          placeholder='Paste a JSON object here to validate against the current schema...'
        />
        <button
          onClick={handleValidateObject}
          disabled={isLoading || !validationObject.trim()}
          className="mt-2 px-4 py-2 bg-teal-500 hover:bg-teal-600 text-white font-semibold rounded-md disabled:opacity-50"
        >
          Validate Object
        </button>
        {validationResult && (
          <div className={`mt-3 p-3 rounded-md ${validationResult.is_valid ? 'bg-green-700' : 'bg-red-700'}`}>
            <p className="font-semibold">{validationResult.is_valid ? 'Validation Passed!' : 'Validation Failed!'}</p>
            {validationResult.errors && validationResult.errors.map((err, index) => (
              <div key={index} className="mt-1 text-sm">
                <p>- Message: {err.message}</p>
                <p>  Path: {err.path.join(' -> ') || 'N/A'}</p>
                <p>  Validator: {err.validator || 'N/A'}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <hr className="my-6 border-gray-700" />
      
      {/* Approve Schema */}
      {schema.status !== 'approved_master' && (
         <div className="mt-4">
         <button
             onClick={handleApproveSchema}
             disabled={isLoading}
             className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-md disabled:opacity-50"
         >
             Approve this Schema as Master
         </button>
         </div>
      )}

      {error && <p className="mt-4 text-red-400">Error: {error}</p>}
      {isLoading && <p className="mt-4 text-yellow-400">Processing...</p>}
    </div>
  );
};

export default SchemaDisplayAndActions;