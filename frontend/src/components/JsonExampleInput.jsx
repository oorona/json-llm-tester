import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = ''; // Relative path for API calls

const JsonExampleInput = ({ onSchemaGenerated, onExampleSubmitted }) => {
  const [jsonInput, setJsonInput] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [submittedExample, setSubmittedExample] = useState(null);
  const [generatedSchema, setGeneratedSchema] = useState(null);

  const handleJsonInputChange = (event) => {
    setJsonInput(event.target.value);
  };

  const handleDescriptionChange = (event) => {
    setDescription(event.target.value);
  };

  const handleSubmitExample = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setGeneratedSchema(null); // Clear previous schema
    setSubmittedExample(null); // Clear previous example

    let parsedJsonContent;
    try {
      parsedJsonContent = JSON.parse(jsonInput);
    } catch (e) {
      setError('Invalid JSON input. Please check the syntax.');
      setIsLoading(false);
      return;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/json-examples/`, {
        content: parsedJsonContent,
        description: description,
      });
      setSubmittedExample(response.data);
      if(onExampleSubmitted) onExampleSubmitted(response.data);
      // Automatically trigger schema generation for now, or have a separate button
      await handleGenerateSchema(response.data.id, parsedJsonContent);
    } catch (err) {
      console.error('Error submitting JSON example:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to submit JSON example.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateSchema = async (exampleId, exampleContent) => {
    setIsLoading(true);
    setError(null);
    setGeneratedSchema(null);
    try {
      const url = `${API_BASE_URL}/json-examples/${exampleId}/generate-schema`;
      console.log(`Attempting to generate schema for exampleId: ${exampleId} with URL: ${url}`);
      
      const response = await axios.post(url);      
      setGeneratedSchema(response.data);
      if(onSchemaGenerated) onSchemaGenerated(response.data);
    } catch (err) {
      console.error('Error generating schema:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to generate schema.');
      // If schema gen fails, still keep the submitted example visible
      if(submittedExample === null && exampleId && exampleContent){
        // This is a fallback if handleSubmitExample's setSubmittedExample hasn't updated yet
        // or if called directly.
        setSubmittedExample({id: exampleId, content: exampleContent, description });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const prettyPrintJson = (json) => {
    if (!json) return '';
    try {
      return JSON.stringify(json, null, 2);
    } catch (e) {
      return "Error pretty-printing JSON.";
    }
  };

  return (
    <div className="p-6 bg-gray-800 rounded-lg shadow-xl mb-8">
      <h3 className="text-xl font-semibold mb-4 text-blue-300">1. Provide JSON Example</h3>
      <form onSubmit={handleSubmitExample}>
        <div className="mb-4">
          <label htmlFor="jsonDescription" className="block text-sm font-medium text-gray-300 mb-1">
            Description (Optional):
          </label>
          <input
            type="text"
            id="jsonDescription"
            value={description}
            onChange={handleDescriptionChange}
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., User profile structure"
          />
        </div>
        <div className="mb-4">
          <label htmlFor="jsonInput" className="block text-sm font-medium text-gray-300 mb-1">
            Paste your example JSON here:
          </label>
          <textarea
            id="jsonInput"
            rows="10"
            value={jsonInput}
            onChange={handleJsonInputChange}
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
            placeholder='{ "key": "value", "nested": { "id": 1 } }'
          />
        </div>
        <button
          type="submit"
          disabled={isLoading || !jsonInput.trim()}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md disabled:opacity-50"
        >
          {isLoading ? 'Processing...' : 'Submit Example & Generate Schema'}
        </button>
      </form>

      {error && <p className="mt-4 text-red-400">Error: {error}</p>}

      {submittedExample && !generatedSchema && !isLoading && !error && (
         <p className="mt-4 text-yellow-400">Submitted example, waiting for schema or schema generation failed...</p>
      )}

      {generatedSchema && (
        <div className="mt-6">
          <h4 className="text-lg font-semibold text-green-400">Schema Generated (ID: {generatedSchema.id}, Version: {generatedSchema.version})</h4>
          <p className="text-sm text-gray-400">Status: {generatedSchema.status}</p>
          <pre className="mt-2 p-4 bg-gray-900 rounded-md overflow-x-auto text-sm">
            {prettyPrintJson(generatedSchema.schema_content)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default JsonExampleInput;