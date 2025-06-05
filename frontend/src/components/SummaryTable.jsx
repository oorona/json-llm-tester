// frontend/src/components/SummaryTable.jsx
import React from 'react';

const SummaryTable = ({ summaryData }) => {
  if (!summaryData || !summaryData.llm_summaries || summaryData.llm_summaries.length === 0) {
    return <p className="text-gray-400">No summary data available for this test run, or results are still processing.</p>;
  }

  return (
    <div className="overflow-x-auto shadow-md rounded-lg">
      <h4 className="text-lg font-semibold text-blue-300 mb-2">LLM Performance Summary</h4>
      <table className="min-w-full text-sm text-left text-gray-300 bg-gray-750">
        <thead className="text-xs text-gray-200 uppercase bg-gray-700">
          <tr>
            <th scope="col" className="px-4 py-3">LLM Model ID</th>
            <th scope="col" className="px-4 py-3 text-center">Total Tests</th>
            <th scope="col" className="px-4 py-3 text-center">Valid JSON Output</th>
            <th scope="col" className="px-4 py-3 text-center">Schema Compliant</th>
            <th scope="col" className="px-4 py-3 text-center">Compliance %</th>
            <th scope="col" className="px-4 py-3 text-center">Avg. Exec Time (ms)</th>
            <th scope="col" className="px-4 py-3 text-center">Total Tokens</th>
          </tr>
        </thead>
        <tbody>
          {summaryData.llm_summaries.map(llmSummary => (
            <tr key={llmSummary.target_llm_model_id} className="border-b border-gray-700 hover:bg-gray-600">
              <td className="px-4 py-2 font-medium whitespace-nowrap">{llmSummary.target_llm_model_id}</td>
              <td className="px-4 py-2 text-center">{llmSummary.total_tests}</td>
              <td className="px-4 py-2 text-center">{llmSummary.successful_parses}</td>
              <td className="px-4 py-2 text-center">{llmSummary.schema_compliant_tests}</td>
              <td className="px-4 py-2 text-center">{llmSummary.schema_compliance_percentage}%</td>
              <td className="px-4 py-2 text-center">{llmSummary.average_execution_time_ms ?? 'N/A'}</td>
              <td className="px-4 py-2 text-center">{llmSummary.total_tokens_used ?? 'N/A'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default SummaryTable;