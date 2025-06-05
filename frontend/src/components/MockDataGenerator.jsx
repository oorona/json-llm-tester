// frontend/src/components/MockDataGenerator.jsx
import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = ''; // Relative path

const MockDataGenerator = ({ approvedSchema, selectedAssistantLlm, onMockDataGenerated }) => {
  const [promptText, setPromptText] = useState('');
  const [itemCount, setItemCount] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!approvedSchema || approvedSchema.status !== 'approved_master') {
    return (
      <div className="p-6 bg-gray-800 rounded-lg shadow-xl">
        <h3 className="text-xl font-semibold text-blue-300 mb-3">2. Generate Mock Input Data</h3>
        <p className="text-yellow-400">Please approve a master schema in Phase 1 before generating mock data.</p>
      </div>
    );
  }

  if (!selectedAssistantLlm) {
    return (
      <div className="p-6 bg-gray-800 rounded-lg shadow-xl">
        <h3 className="text-xl font-semibold text-blue-300 mb-3">2. Generate Mock Input Data</h3>
        <p className="text-yellow-400">Please select an Assistant LLM in Phase 0 before generating mock data.</p>
      </div>
    );
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!promptText.trim() || itemCount <= 0) {
      setError("Please provide a valid prompt and a positive number of items.");
      return;
    }
    setIsLoading(true);
    setError(null);

    try {
      const url = `${API_BASE_URL}json-schemas/${approvedSchema.id}/generate-mock-data`;
      console.log("Generating mock data with URL:", url, "Payload:", { prompt_text: promptText, desired_item_count: parseInt(itemCount, 10) });

      const response = await axios.post(url, {
        prompt_text: promptText,
        desired_item_count: parseInt(itemCount, 10),
      });

      console.log("Mock data generation response:", response.data);
      if (onMockDataGenerated) {
        onMockDataGenerated(response.data.prompt_details); // Pass the prompt details which include items
      }
      setPromptText(''); // Clear form
    } catch (err) {
      console.error('Error generating mock data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to generate mock data.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-800 rounded-lg shadow-xl">
      <h3 className="text-xl font-semibold text-blue-300 mb-3">
        2. Generate Mock Input Data (for Schema ID: {approvedSchema.id} - {approvedSchema.name})
      </h3>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="mockDataPrompt" className="block text-sm font-medium text-gray-300 mb-1">
            Describe the mock data scenarios:
          </label>
          <textarea
            id="mockDataPrompt"
            rows="4"
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 text-white"
            placeholder="e.g., Generate user profiles with a variety of names, emails, and short, quirky bios."
          />
        </div>
        <div className="mb-4">
          <label htmlFor="itemCount" className="block text-sm font-medium text-gray-300 mb-1">
            Number of mock data items to generate:
          </label>
          <input
            type="number"
            id="itemCount"
            value={itemCount}
            onChange={(e) => setItemCount(parseInt(e.target.value, 10))}
            min="1"
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 text-white"
          />
        </div>
        <button
          type="submit"
          disabled={isLoading || !promptText.trim() || itemCount <= 0}
          className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-md disabled:opacity-50"
        >
          {isLoading ? 'Generating Mock Data...' : 'Generate Mock Data with Assistant LLM'}
        </button>
      </form>
      {error && <p className="mt-4 text-red-400">Error: {error}</p>}
    </div>
  );
};

export default MockDataGenerator;