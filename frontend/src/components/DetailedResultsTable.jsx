// frontend/src/components/DetailedResultsTable.jsx
import React from 'react';

const DetailedResultsTable = ({ results }) => {
  if (!results || results.length === 0) {
    return <p className="mt-4 text-gray-400">No detailed results available for this selection, or results are still processing.</p>;
  }
  
  const prettyPrintJson = (json) => {
     if (json === null || json === undefined) return 'N/A';
     try { return JSON.stringify(json, null, 2); } 
     catch (e) { return "Error displaying JSON."; }
  };

  return (
    <div className="mt-6 shadow-md rounded-lg">
      <h4 className="text-lg font-semibold text-blue-300 mb-2">Detailed Test Case Results</h4>
      <div className="max-h-[600px] overflow-y-auto overflow-x-auto">
        <table className="min-w-full text-xs text-left text-gray-300 bg-gray-750">
          <thead className="text-xs text-gray-200 uppercase bg-gray-700 sticky top-0">
            <tr>
              <th scope="col" className="px-3 py-2">LLM</th>
              <th scope="col" className="px-3 py-2">Input Data (Snippet)</th>
              <th scope="col" className="px-3 py-2">Raw Output (Snippet)</th>
              <th scope="col" className="px-3 py-2">Valid JSON?</th>
              <th scope="col" className="px-3 py-2">Schema Compliant?</th>
              <th scope="col" className="px-3 py-2">Exec Time (ms)</th>
              <th scope="col" className="px-3 py-2">Tokens</th>
              <th scope="col" className="px-3 py-2">Errors</th>
            </tr>
          </thead>
          <tbody>
            {results.map(result => (
              <tr key={result.id} className="border-b border-gray-700 hover:bg-gray-600">
                <td className="px-3 py-2 align-top font-medium">{result.target_llm_model_id}</td>
                <td className="px-3 py-2 align-top"><pre className="whitespace-pre-wrap max-w-xs truncate">{prettyPrintJson(result.mock_input_data_used)}</pre></td>
                <td className="px-3 py-2 align-top"><pre className="whitespace-pre-wrap max-w-xs truncate">{result.llm_raw_output || 'N/A'}</pre></td>
                <td className={`px-3 py-2 align-top ${result.parse_status ? 'text-green-400' : 'text-red-400'}`}>{result.parse_status === null ? 'N/A' : result.parse_status ? 'Yes' : 'No'}</td>
                <td className={`px-3 py-2 align-top ${result.schema_compliance_status === 'Pass' ? 'text-green-400' : (result.schema_compliance_status === 'Fail' ? 'text-red-400' : 'text-yellow-400')}`}>{result.schema_compliance_status || 'N/A'}</td>
                <td className="px-3 py-2 align-top">{result.execution_time_ms !== null ? result.execution_time_ms.toFixed(0) : 'N/A'}</td>
                <td className="px-3 py-2 align-top">{result.tokens_used ?? 'N/A'}</td>
                <td className="px-3 py-2 align-top">
                  {result.error_message ? <span className="text-red-400">{result.error_message}</span> : 
                   (result.validation_errors && result.validation_errors.length > 0 ? 
                     <pre className="text-red-400 whitespace-pre-wrap max-w-xs truncate">{prettyPrintJson(result.validation_errors)}</pre> : 'None')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DetailedResultsTable;