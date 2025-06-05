// frontend/src/components/TestRunSelector.jsx
import React from 'react';

const TestRunSelector = ({ testRuns, selectedTestRunId, onTestRunSelect, isLoading }) => {
  if (isLoading) {
    return <p className="text-yellow-400">Loading test runs...</p>;
  }

  if (!testRuns || testRuns.length === 0) {
    return <p className="text-gray-400">No test runs found. Please initiate a test run in Phase 4.</p>;
  }

  return (
    <div className="mb-6">
      <label htmlFor="test-run-select" className="block mb-2 text-lg font-medium text-gray-300">
        Select Test Run to View Results:
      </label>
      <select
        id="test-run-select"
        value={selectedTestRunId || ''}
        onChange={(e) => onTestRunSelect(e.target.value ? parseInt(e.target.value) : null)}
        className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 appearance-none text-white"
      >
        <option value="" disabled={!!selectedTestRunId}>-- Select a Test Run --</option>
        {testRuns.map(run => (
          <option key={run.id} value={run.id}>
            {run.name || `Test Run ID: ${run.id}`} (Status: {run.status}, Created: {new Date(run.created_at).toLocaleString()})
          </option>
        ))}
      </select>
    </div>
  );
};

export default TestRunSelector;