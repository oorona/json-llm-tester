// frontend/src/components/TestRunner.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = '';

const TestRunner = ({ allAvailableModels, approvedSchemas, mockDataPrompts, masterPrompts, onTestRunInitiated }) => {
  const [selectedMasterPromptId, setSelectedMasterPromptId] = useState('');
  const [selectedMockDataPromptId, setSelectedMockDataPromptId] = useState('');
  const [selectedTargetLlmIds, setSelectedTargetLlmIds] = useState([]);
  const [selectedMasterSchemaId, setSelectedMasterSchemaId] = useState('');
  const [testRunName, setTestRunName] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Effect to auto-select the first available approved schema if one exists
  useEffect(() => {
     if (approvedSchemas && approvedSchemas.length > 0 && !selectedMasterSchemaId) {
         setSelectedMasterSchemaId(approvedSchemas[0].id.toString());
     } else if ((!approvedSchemas || approvedSchemas.length === 0) && selectedMasterSchemaId) {
         setSelectedMasterSchemaId(''); // Clear if no approved schemas
     }
  }, [approvedSchemas, selectedMasterSchemaId]);


  const handleTargetLlmSelection = (event) => {
    const options = event.target.options;
    const value = [];
    for (let i = 0, l = options.length; i < l; i++) {
      if (options[i].selected) {
        value.push(options[i].value);
      }
    }
    setSelectedTargetLlmIds(value);
  };

  const handleSubmitTestRun = async (event) => {
    event.preventDefault();
    if (!selectedMasterPromptId || !selectedMockDataPromptId || selectedTargetLlmIds.length === 0 || !selectedMasterSchemaId) {
      setError("Please select a master prompt, a mock data set, at least one target LLM, and an approved master schema.");
      return;
    }
    setIsLoading(true); setError(null);
    try {
      const payload = {
        name: testRunName.trim() || `Test Run ${new Date().toLocaleString()}`,
        master_prompt_id: parseInt(selectedMasterPromptId),
        mock_data_prompt_id: parseInt(selectedMockDataPromptId),
        target_llm_model_ids: selectedTargetLlmIds,
        master_schema_id: parseInt(selectedMasterSchemaId),
      };
      console.log("Initiating test run with payload:", payload);
      const response = await axios.post(`${API_BASE_URL}/test-runs/`, payload);
      onTestRunInitiated(response.data); // Notify parent App component
      alert(`Test run (ID: ${response.data.id}) initiated successfully with status: ${response.data.status}`);
      // Clear form or give other feedback
      setTestRunName('');

    } catch (err) {
      console.error("Error initiating test run:", err);
      setError(err.response?.data?.detail || err.message || "Failed to initiate test run.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 border border-gray-700 rounded-md">
      <form onSubmit={handleSubmitTestRun} className="space-y-4">
        <div>
          <label htmlFor="testRunName" className="block text-sm font-medium text-gray-300 mb-1">Test Run Name (Optional):</label>
          <input
            type="text"
            id="testRunName"
            value={testRunName}
            onChange={(e) => setTestRunName(e.target.value)}
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
            placeholder="e.g., My LLM Comparison v1"
          />
        </div>

        <div>
          <label htmlFor="masterSchemaSelect" className="block text-sm font-medium text-gray-300 mb-1">Master Schema (Approved):</label>
          <select
            id="masterSchemaSelect"
            value={selectedMasterSchemaId}
            onChange={(e) => setSelectedMasterSchemaId(e.target.value)}
            required
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white appearance-none"
          >
            <option value="" disabled>-- Select Master Schema --</option>
            {approvedSchemas && approvedSchemas.map(schema => (
              <option key={schema.id} value={schema.id}>{schema.name || `Schema ID ${schema.id}`} (v{schema.version})</option>
            ))}
          </select>
          {(!approvedSchemas || approvedSchemas.length === 0) && <p className="text-xs text-yellow-500 mt-1">No 'approved_master' schemas found. Please approve a schema in Phase 1.</p>}
        </div>

        <div>
          <label htmlFor="masterPromptSelectRun" className="block text-sm font-medium text-gray-300 mb-1">Master Prompt:</label>
          <select
            id="masterPromptSelectRun"
            value={selectedMasterPromptId}
            onChange={(e) => setSelectedMasterPromptId(e.target.value)}
            required
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white appearance-none"
          >
            <option value="" disabled>-- Select Master Prompt --</option>
            {masterPrompts && masterPrompts.map(prompt => (
              <option key={prompt.id} value={prompt.id}>{prompt.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="mockDataPromptSelectRun" className="block text-sm font-medium text-gray-300 mb-1">Mock Data Set (Prompt):</label>
          <select
            id="mockDataPromptSelectRun"
            value={selectedMockDataPromptId}
            onChange={(e) => setSelectedMockDataPromptId(e.target.value)}
            required
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white appearance-none"
          >
            <option value="" disabled>-- Select Mock Data Set --</option>
            {mockDataPrompts && mockDataPrompts.map(prompt => (
              <option key={prompt.id} value={prompt.id}>{prompt.prompt_text.substring(0,50)}... (ID: {prompt.id}, Items: {prompt.generated_items?.length || 0})</option>
            ))}
          </select>
        </div>
        
        <div>
          <label htmlFor="targetLlmsSelect" className="block text-sm font-medium text-gray-300 mb-1">Target LLMs (select one or more):</label>
          <select
            id="targetLlmsSelect"
            multiple
            value={selectedTargetLlmIds}
            onChange={handleTargetLlmSelection}
            required
            className="w-full p-2 h-32 bg-gray-700 border border-gray-600 rounded-md text-white"
          >
            {allAvailableModels && allAvailableModels.map(model => (
              <option key={model.model_id} value={model.model_id}>{model.name} ({model.model_id})</option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={isLoading || !selectedMasterSchemaId || !selectedMasterPromptId || !selectedMockDataPromptId || selectedTargetLlmIds.length === 0}
          className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-md disabled:opacity-50"
        >
          {isLoading ? 'Starting Test Run...' : 'Start Test Run'}
        </button>
        {error && <p className="mt-3 text-red-400">Error: {error}</p>}
      </form>
    </div>
  );
};

export default TestRunner;