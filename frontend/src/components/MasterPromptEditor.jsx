// frontend/src/components/MasterPromptEditor.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = ''; // Relative path

const MasterPromptEditor = ({ approvedSchema, selectedAssistantLlm, onMasterPromptSaved, selectedMasterPrompt, onClearSelectedMasterPrompt }) => {
  const [promptName, setPromptName] = useState('');
  const [promptContent, setPromptContent] = useState("Generate a JSON object based on the following input data: {{INPUT_DATA}}. \nThe output must strictly conform to the provided JSON schema. Only output the JSON object itself, with no additional text or explanations.");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refinementFeedback, setRefinementFeedback] = useState('');
  const [currentMasterPromptId, setCurrentMasterPromptId] = useState(null);
  const [isEditing, setIsEditing] = useState(false); // To differentiate create vs update

  useEffect(() => {
    if (selectedMasterPrompt) {
      setPromptName(selectedMasterPrompt.name || '');
      setPromptContent(selectedMasterPrompt.prompt_content || '');
      setCurrentMasterPromptId(selectedMasterPrompt.id);
      setIsEditing(true);
    } else {
      // Reset form for new prompt creation
      setPromptName(`MasterPrompt_${Date.now().toString().slice(-6)}`); // Default unique name
      setPromptContent("Generate a JSON object based on the following input data: {{INPUT_DATA}}. \nThe output must strictly conform to the provided JSON schema. Only output the JSON object itself, with no additional text or explanations.");
      setCurrentMasterPromptId(null);
      setIsEditing(false);
    }
    setError(null); // Clear errors when selection changes
    setRefinementFeedback('');
  }, [selectedMasterPrompt]);
  
  const handleRefinementFeedbackChange = (event) => {
    setRefinementFeedback(event.target.value);
  };
  
  const handleSaveOrUpdatePrompt = async () => {
    if (!promptName.trim() || !promptContent.trim()) {
      setError("Prompt name and content cannot be empty.");
      return;
    }
    if (!promptContent.includes("{{INPUT_DATA}}")) {
      setError("Master prompt content must include the placeholder '{{INPUT_DATA}}'.");
      return;
    }

    setIsLoading(true); setError(null);
    const payload = {
      name: promptName,
      prompt_content: promptContent,
      target_schema_id: approvedSchema ? approvedSchema.id : null,
    };

    try {
      let response;
      if (isEditing && currentMasterPromptId) {
        // Update existing prompt
        console.log("Updating master prompt ID:", currentMasterPromptId, "Payload:", payload);
        response = await axios.put(`${API_BASE_URL}/master-prompts/${currentMasterPromptId}`, payload);
      } else {
        // Create new prompt
        console.log("Creating new master prompt. Payload:", payload);
        response = await axios.post(`${API_BASE_URL}/master-prompts/`, payload);
      }
      onMasterPromptSaved(response.data); // Notify parent
      // If creating new, set currentMasterPromptId and isEditing for subsequent edits/refinements
      if (!isEditing) {
         setCurrentMasterPromptId(response.data.id);
         setIsEditing(true); // Switch to edit mode for the newly created prompt
      }
      alert(`Master Prompt ${isEditing ? 'updated' : 'saved'} successfully!`);
    } catch (err) {
      console.error(`Error ${isEditing ? 'updating' : 'saving'} master prompt:`, err);
      setError(err.response?.data?.detail || err.message || `Failed to ${isEditing ? 'update' : 'save'} master prompt.`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLlmRefinePrompt = async () => {
    if (!currentMasterPromptId) {
      setError("Please save the prompt first before refining.");
      return;
    }
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
      const url = `${API_BASE_URL}/master-prompts/${currentMasterPromptId}/refine-with-llm`;
      console.log("Refining master prompt ID:", currentMasterPromptId, "Feedback:", refinementFeedback);
      const response = await axios.post(url, { feedback: refinementFeedback });
      onMasterPromptSaved(response.data); // Notify parent of the update
      setPromptContent(response.data.prompt_content); // Update local content
      setRefinementFeedback(''); // Clear input
      alert("Master Prompt refined successfully by LLM!");
    } catch (err) {
      console.error("Error refining master prompt with LLM:", err);
      setError(err.response?.data?.detail || err.message || "Failed to refine master prompt.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewPrompt = () => {
     if (onClearSelectedMasterPrompt) {
         onClearSelectedMasterPrompt(); // This will trigger useEffect to reset the form
     } else { // Fallback if the prop is not passed, directly reset local state
         setPromptName(`MasterPrompt_${Date.now().toString().slice(-6)}`);
         setPromptContent("Generate a JSON object based on the following input data: {{INPUT_DATA}}. \nThe output must strictly conform to the provided JSON schema. Only output the JSON object itself, with no additional text or explanations.");
         setCurrentMasterPromptId(null);
         setIsEditing(false);
         setError(null);
         setRefinementFeedback('');
     }
  };

  return (
    <div className="p-6 bg-gray-800 rounded-lg shadow-xl">
      <div className="flex justify-between items-center mb-3">
         <h3 className="text-xl font-semibold text-blue-300">
             {isEditing ? `Edit Master Prompt: ${promptName}` : "Create New Master Prompt"}
             {isEditing && currentMasterPromptId && ` (ID: ${currentMasterPromptId})`}
         </h3>
         <button
             onClick={handleNewPrompt}
             className="px-3 py-1 text-sm bg-gray-600 hover:bg-gray-500 text-white rounded"
         >
             + New Prompt
         </button>
      </div>

      {approvedSchema ? (
         <p className="text-xs text-gray-400 mb-3">
             Targeting Schema: {approvedSchema.name} (ID: {approvedSchema.id}, Status: {approvedSchema.status})
         </p>
      ) : (
         <p className="text-xs text-yellow-400 mb-3">
             Warning: No approved master schema selected/available. The prompt will be saved without a specific schema link.
         </p>
      )}

      <div className="mb-4">
        <label htmlFor="masterPromptName" className="block text-sm font-medium text-gray-300 mb-1">
          Prompt Name:
        </label>
        <input
          type="text"
          id="masterPromptName"
          value={promptName}
          onChange={(e) => setPromptName(e.target.value)}
          className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 text-white"
          placeholder="e.g., UserProfileGenerator_v1"
        />
      </div>

      <div className="mb-4">
        <label htmlFor="masterPromptContent" className="block text-sm font-medium text-gray-300 mb-1">
          {/* Ensure this is treated as a single string literal by JSX */}
          {'Master Prompt Content (use `{{INPUT_DATA}}` as placeholder):'}
        </label>
        <textarea
          id="masterPromptContent"
          rows="10"
          value={promptContent}
          onChange={(e) => setPromptContent(e.target.value)}
          className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm text-white"
          placeholder="Your prompt instructing the LLM..."
        />
      </div>
      <button
        onClick={handleSaveOrUpdatePrompt}
        disabled={isLoading || !promptName.trim() || !promptContent.trim()}
        className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-md disabled:opacity-50 mb-6"
      >
        {isLoading ? 'Saving...' : (isEditing ? 'Update Master Prompt' : 'Save New Master Prompt')}
      </button>

      {isEditing && currentMasterPromptId && ( // Show refinement options only if editing an existing prompt
        <>
          <hr className="my-6 border-gray-700" />
          <div className="mb-4">
            <h4 className="text-lg text-blue-300 mb-2">Refine Master Prompt with Assistant LLM</h4>
            <textarea
              id="masterPromptRefinementFeedback"
              rows="3"
              value={refinementFeedback}
              onChange={handleRefinementFeedbackChange}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 text-white"
              placeholder="e.g., Make it more concise, or ask for specific output formatting details."
            />
            <button
              onClick={handleLlmRefinePrompt}
              disabled={isLoading || !refinementFeedback.trim() || !selectedAssistantLlm}
              className="mt-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
              title={!selectedAssistantLlm ? "Select Assistant LLM first for refinement" : ""}
            >
              Refine Prompt with LLM
            </button>
          </div>
        </>
      )}
      {error && <p className="mt-4 text-red-400">Error: {error}</p>}
    </div>
  );
};

export default MasterPromptEditor;