// frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Import all necessary components
import JsonExampleInput from './components/JsonExampleInput';
import SchemaDisplayAndActions from './components/SchemaDisplayAndActions';
import MockDataGenerator from './components/MockDataGenerator';
import MockDataManagement from './components/MockDataManagement';
import MasterPromptEditor from './components/MasterPromptEditor';
import TestRunner from './components/TestRunner';
import TestRunSelector from './components/TestRunSelector';
import ResultsDashboard from './components/ResultsDashboard';

function App() {
  // Phase 0: LLM Selection
  const [models, setModels] = useState([]); // All available LLMs from /models
  const [loadingModels, setLoadingModels] = useState(true);
  const [modelError, setModelError] = useState(null);
  const [selectedAssistantLlm, setSelectedAssistantLlm] = useState('');

  // Phase 1: Schema Definition
  const [currentJsonExample, setCurrentJsonExample] = useState(null);
  const [currentJsonSchema, setCurrentJsonSchema] = useState(null); // Holds the active schema
  const [allJsonSchemas, setAllJsonSchemas] = useState([]); // For selecting master schema
  const [loadingSchemas, setLoadingSchemas] = useState(false);

  // Phase 2: Mock Data
  const [currentMockDataPrompt, setCurrentMockDataPrompt] = useState(null); // Holds prompt & its generated items
  const [allMockDataPrompts, setAllMockDataPrompts] = useState([]); // For selecting mock data set
  const [loadingMockDataPrompts, setLoadingMockDataPrompts] = useState(false);

  // Phase 3: Master Prompt
  const [allMasterPrompts, setAllMasterPrompts] = useState([]); // For selecting master prompt
  const [selectedMasterPromptForEditing, setSelectedMasterPromptForEditing] = useState(null); 
  const [loadingMasterPrompts, setLoadingMasterPrompts] = useState(false);

  // Phase 4 & 5: Test Runs and Results
  const [currentTestRunInitiated, setCurrentTestRunInitiated] = useState(null); // Stores the initially returned TestRun object after POST /test-runs/
  const [allTestRuns, setAllTestRuns] = useState([]); // List of all test runs for TestRunSelector
  const [loadingTestRuns, setLoadingTestRuns] = useState(false);
  const [selectedTestRunIdForResults, setSelectedTestRunIdForResults] = useState(null); // ID of run to show in dashboard

  const API_BASE_URL = ''; // Relative path for API calls

  // --- Data Fetching Effects ---
  useEffect(() => {
    const fetchModels = async () => {
      try {
        setLoadingModels(true);
        const response = await axios.get(`${API_BASE_URL}/models`);
        setModels(response.data || []);
        setModelError(null);
      } catch (err) {
        setModelError(err.response?.data?.detail || err.message || 'Failed to fetch models.');
        setModels([]);
        console.error("App.jsx - Fetch models error:", err);
      } finally {
        setLoadingModels(false);
      }
    };
    fetchModels();
  }, []);

  const fetchAllJsonSchemas = async () => {
    setLoadingSchemas(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/json-schemas/`);
      setAllJsonSchemas(response.data || []);
    } catch (error) {
      console.error("Error fetching all JSON schemas:", error);
      setAllJsonSchemas([]);
    } finally {
      setLoadingSchemas(false);
    }
  };

  const fetchAllMockDataPrompts = async () => {
    setLoadingMockDataPrompts(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/mock-data/prompts/`);
      setAllMockDataPrompts(response.data || []);
    } catch (error) {
      console.error("Error fetching all mock data prompts:", error);
      setAllMockDataPrompts([]);
    } finally {
      setLoadingMockDataPrompts(false);
    }
  };

  const fetchAllMasterPrompts = async () => {
    setLoadingMasterPrompts(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/master-prompts/`);
      setAllMasterPrompts(response.data || []);
    } catch (error) {
      console.error("Error fetching all master prompts:", error);
      setAllMasterPrompts([]);
    } finally {
      setLoadingMasterPrompts(false);
    }
  };

  const fetchAllTestRuns = async () => {
    setLoadingTestRuns(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/test-runs/`);
      setAllTestRuns(response.data || []);
    } catch (error) {
      console.error("Error fetching all test runs:", error);
      setAllTestRuns([]);
    } finally {
      setLoadingTestRuns(false);
    }
  };
  
  // Initial data fetching for dropdowns needed by TestRunner and ResultsDashboard
  useEffect(() => {
    fetchAllJsonSchemas();
    fetchAllMockDataPrompts();
    fetchAllMasterPrompts();
    fetchAllTestRuns(); // Fetch test runs for the selector
  }, []);


  // --- Callback Handlers from Child Components ---
  const handleExampleSubmittedInApp = (example) => {
    setCurrentJsonExample(example);
    setCurrentJsonSchema(null); 
    setCurrentMockDataPrompt(null);
    setSelectedMasterPromptForEditing(null);
  };

  const handleSchemaGeneratedOrUpdatedInApp = (schema) => {
    setCurrentJsonSchema(schema);
    setCurrentMockDataPrompt(null); 
    setSelectedMasterPromptForEditing(null);
    fetchAllJsonSchemas(); // Refresh the list of all schemas for selectors
  };

  const handleMockDataGeneratedInApp = (mockDataPromptWithItems) => {
    setCurrentMockDataPrompt(mockDataPromptWithItems);
    fetchAllMockDataPrompts(); // Refresh the list of mock data prompts
  };
  
  const handleMockDataItemsUpdatedInApp = (updatedMockDataPromptWithItems) => {
    setCurrentMockDataPrompt(updatedMockDataPromptWithItems);
    // Optionally, refresh the main list if counts/etc. displayed there
    // fetchAllMockDataPrompts(); 
  };
  
  const handleMasterPromptSavedInApp = (savedPrompt) => {
    setSelectedMasterPromptForEditing(savedPrompt); 
    fetchAllMasterPrompts(); // Refresh list of master prompts
  };

  const handleClearSelectedMasterPromptForEditing = () => {
    setSelectedMasterPromptForEditing(null); 
  };

  const handleTestRunInitiated = (testRun) => {
    console.log("App: Test Run Initiated/Updated:", testRun);
    setCurrentTestRunInitiated(testRun); 
    fetchAllTestRuns(); // Refresh the list of all test runs
    setSelectedTestRunIdForResults(testRun.id); // Auto-select the new run for viewing results
  };

  const handleSelectTestRunForResults = (runId) => {
    setSelectedTestRunIdForResults(runId);
    // The ResultsDashboard component will fetch its own details based on this ID
  };
  
  // Derived state: find an approved schema to pass to components that need it
  const approvedMasterSchemaForPhases = 
    (currentJsonSchema && currentJsonSchema.status === 'approved_master') ? currentJsonSchema 
    : (Array.isArray(allJsonSchemas) ? allJsonSchemas.find(s => s.status === 'approved_master') : null);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4 md:p-8 font-sans">
      <header className="mb-10">
        <h1 className="text-3xl md:text-4xl font-bold text-center text-blue-400">LLM JSON Generation Evaluator</h1>
      </header>

      <main className="max-w-6xl mx-auto space-y-12"> {/* Increased max-width */}
        {/* Phase 0: Assistant LLM Selection */}
        <section className="p-6 bg-gray-800 rounded-lg shadow-xl">
          <h2 className="text-2xl font-semibold mb-4 text-blue-300">Phase 0: Assistant LLM Selection</h2>
          {loadingModels && <p className="text-yellow-400">Loading LLM models...</p>}
          {modelError && <p className="text-red-400">Error fetching models: {modelError}</p>}
          {!loadingModels && !modelError && Array.isArray(models) && models.length > 0 && (
            <div>
              <label htmlFor="llm-select" className="block mb-2 text-lg">Select Assistant LLM:</label>
              <select 
                id="llm-select" 
                value={selectedAssistantLlm} 
                onChange={(e) => setSelectedAssistantLlm(e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 appearance-none text-white"
              >
                <option value="" disabled className="text-gray-500">-- Select an LLM --</option>
                {models.map((model) => (
                  <option key={model.model_id} value={model.model_id} className="text-white">
                    {model.name} ({model.model_id})
                  </option>
                ))}
              </select>
              {selectedAssistantLlm && <p className="mt-3 text-green-400">Selected Assistant LLM: {selectedAssistantLlm}</p>}
            </div>
          )}
          {!loadingModels && !modelError && (!models || models.length === 0) && (
            <p className="text-gray-400">No LLM models available. Ensure backend and LLM service are running and configured.</p>
          )}
        </section>

        {/* Phase 1: Define Target JSON Structure & Schema */}
        <section className="p-6 bg-gray-800 rounded-lg shadow-xl">
          <h2 className="text-2xl font-semibold mb-4 text-blue-300">Phase 1: Define Target JSON Structure & Schema</h2>
          <JsonExampleInput 
            onSchemaGenerated={handleSchemaGeneratedOrUpdatedInApp} 
            onExampleSubmitted={handleExampleSubmittedInApp}
            selectedAssistantLlm={selectedAssistantLlm}
          />
          {currentJsonSchema && (
            <SchemaDisplayAndActions 
              schema={currentJsonSchema} 
              onSchemaUpdated={handleSchemaGeneratedOrUpdatedInApp}
              selectedAssistantLlm={selectedAssistantLlm}
            />
          )}
        </section>
        
        {/* Phase 2: Generate and Refine Mock Input Data */}
        <section className="p-6 bg-gray-800 rounded-lg shadow-xl">
          <h2 className="text-2xl font-semibold mb-4 text-blue-300">Phase 2: Generate and Refine Mock Input Data</h2>
          <MockDataGenerator 
            approvedSchema={approvedMasterSchemaForPhases}
            selectedAssistantLlm={selectedAssistantLlm}
            onMockDataGenerated={handleMockDataGeneratedInApp}
          />
          {currentMockDataPrompt && ( 
            <MockDataManagement 
              mockDataPrompt={currentMockDataPrompt} 
              onItemsUpdated={handleMockDataItemsUpdatedInApp} 
            />
          )}
        </section>

        {/* Phase 3: Craft Master Prompt */}
        <section className="p-6 bg-gray-800 rounded-lg shadow-xl">
          <h2 className="text-2xl font-semibold mb-4 text-blue-300">Phase 3: Craft Master Prompt</h2>
          <div className="mb-4">
             <label htmlFor="master-prompt-select-main" className="block mb-1 text-sm font-medium text-gray-300">Load Existing or Create New Master Prompt:</label>
             <select
                 id="master-prompt-select-main"
                 value={selectedMasterPromptForEditing ? selectedMasterPromptForEditing.id : ""}
                 onChange={(e) => {
                     const promptId = e.target.value;
                     setSelectedMasterPromptForEditing(promptId ? allMasterPrompts.find(p => p.id === parseInt(promptId)) || null : null);
                 }}
                 className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 appearance-none text-white"
             >
                 <option value="">-- Create New Master Prompt --</option>
                 {loadingMasterPrompts && <option disabled>Loading prompts...</option>}
                 {Array.isArray(allMasterPrompts) && allMasterPrompts.map(prompt => (
                     <option key={prompt.id} value={prompt.id}>{prompt.name} (ID: {prompt.id})</option>
                 ))}
             </select>
          </div>
          <MasterPromptEditor
            approvedSchema={approvedMasterSchemaForPhases} 
            selectedAssistantLlm={selectedAssistantLlm}
            onMasterPromptSaved={handleMasterPromptSavedInApp}
            selectedMasterPrompt={selectedMasterPromptForEditing} 
            onClearSelectedMasterPrompt={handleClearSelectedMasterPromptForEditing}
          />
        </section>

        {/* Phase 4: Select Models & Run Tests */}
        <section className="p-6 bg-gray-800 rounded-lg shadow-xl">
          <h2 className="text-2xl font-semibold mb-4 text-blue-300">Phase 4: Select Models & Run Tests</h2>
          <TestRunner
            allAvailableModels={models} /* From Phase 0 */
            approvedSchemas={allJsonSchemas.filter(s => s.status === 'approved_master')}
            mockDataPrompts={allMockDataPrompts} 
            masterPrompts={allMasterPrompts}   
            onTestRunInitiated={handleTestRunInitiated}
          />
        </section>

        {/* Phase 5: View & Analyze Results */}
        <section className="p-6 bg-gray-800 rounded-lg shadow-xl">
          <h2 className="text-2xl font-semibold mb-4 text-blue-300">Phase 5: View & Analyze Results</h2>
          <TestRunSelector
             testRuns={allTestRuns}
             selectedTestRunId={selectedTestRunIdForResults}
             onTestRunSelect={handleSelectTestRunForResults}
             isLoading={loadingTestRuns}
          />
          {selectedTestRunIdForResults ? (
             <ResultsDashboard testRunId={selectedTestRunIdForResults} />
          ) : (
            !loadingTestRuns && allTestRuns.length > 0 && 
            <p className="text-center text-gray-400 py-4">Select a test run above to view its dashboard.</p>
          )}
          {!loadingTestRuns && allTestRuns.length === 0 && (
            <p className="text-center text-gray-400 py-4">No test runs available yet. Please initiate a test run in Phase 4.</p>
          )}
        </section>
      </main>

      <footer className="mt-20 pt-8 border-t border-gray-700 text-center text-gray-500">
        <p>&copy; {new Date().getFullYear()} LLM JSON Evaluator</p>
      </footer>
    </div>
  );
}

export default App;