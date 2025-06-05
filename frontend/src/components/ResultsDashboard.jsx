// frontend/src/components/ResultsDashboard.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import SummaryTable from './SummaryTable';
import DetailedResultsTable from './DetailedResultsTable';
// Placeholder for Charting component
// import ChartsContainer from './ChartsContainer'; 

const API_BASE_URL = '';

const ResultsDashboard = ({ testRunId }) => {
  const [testRunDetails, setTestRunDetails] = useState(null); // For full TestRun object with results
  const [summaryData, setSummaryData] = useState(null); // For aggregated summary
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!testRunId) {
      setTestRunDetails(null);
      setSummaryData(null);
      setError(null);
      return;
    }

    const fetchTestRunData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Fetch full test run details (includes individual results)
        const detailsResponse = await axios.get(`${API_BASE_URL}/test-runs/${testRunId}`);
        setTestRunDetails(detailsResponse.data);

        // Fetch summary data
        const summaryResponse = await axios.get(`${API_BASE_URL}/test-runs/${testRunId}/summary-by-llm`);
        setSummaryData(summaryResponse.data);

      } catch (err) {
        console.error(`Error fetching data for Test Run ID ${testRunId}:`, err);
        setError(err.response?.data?.detail || err.message || `Failed to fetch data for Test Run ${testRunId}.`);
        setTestRunDetails(null);
        setSummaryData(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTestRunData();
  }, [testRunId]);

  if (!testRunId) {
    return <p className="text-gray-500 text-center py-4">Select a test run to view its results.</p>;
  }
  if (isLoading) {
    return <p className="text-yellow-400 text-center py-4">Loading results for Test Run ID: {testRunId}...</p>;
  }
  if (error) {
    return <p className="text-red-400 text-center py-4">Error loading results: {error}</p>;
  }
  if (!testRunDetails) {
     return <p className="text-gray-400 text-center py-4">No details found for Test Run ID: {testRunId}.</p>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-2xl font-semibold text-blue-300 mb-1">
          Results Dashboard for: {testRunDetails.name || `Test Run ID ${testRunDetails.id}`}
        </h3>
        <p className="text-sm text-gray-400">Status: {testRunDetails.status} | Completed: {testRunDetails.completed_at ? new Date(testRunDetails.completed_at).toLocaleString() : 'N/A'}</p>
      </div>
      
      <SummaryTable summaryData={summaryData} />

      {/* Placeholder for Charts
      <div className="mt-6 p-4 bg-gray-750 rounded-lg shadow">
          <h4 className="text-lg font-semibold text-blue-300 mb-2">Visualizations (Coming Soon)</h4>
          <p className="text-gray-400">(Charts will be displayed here using Chart.js)</p>
          {/* <ChartsContainer summaryData={summaryData} allResults={testRunDetails.results} /> *}
      </div>
      */}
      
      <DetailedResultsTable results={testRunDetails.results} />
    </div>
  );
};

export default ResultsDashboard;