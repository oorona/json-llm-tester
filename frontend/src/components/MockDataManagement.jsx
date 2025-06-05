// frontend/src/components/MockDataManagement.jsx
import React, { useState } from 'react';
import axios from 'axios';
import MockDataItem from './MockDataItem';

const API_BASE_URL = '';

const MockDataManagement = ({ mockDataPrompt, onItemsUpdated }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newItemContent, setNewItemContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!mockDataPrompt || !mockDataPrompt.id) {
    return <p className="text-sm text-gray-500">Generate or select a mock data set to manage items.</p>;
  }
  
  const handleUpdateItemInList = (updatedItem) => {
     const updatedItems = mockDataPrompt.generated_items.map(item =>
         item.id === updatedItem.id ? updatedItem : item
     );
     onItemsUpdated({ ...mockDataPrompt, generated_items: updatedItems });
  };

  const handleDeleteItemInList = (deletedItemId) => {
     const updatedItems = mockDataPrompt.generated_items.filter(item => item.id !== deletedItemId);
     onItemsUpdated({ ...mockDataPrompt, generated_items: updatedItems });
  };

  const handleAddNewItem = async (event) => {
     event.preventDefault();
     let parsedContent;
     try {
         parsedContent = JSON.parse(newItemContent);
     } catch (e) {
         setError("Invalid JSON for new item.");
         return;
     }
     setIsLoading(true); setError(null);
     try {
         const response = await axios.post(`${API_BASE_URL}/mock-data//prompts/${mockDataPrompt.id}/items/`, {
             item_content: parsedContent
         });
         const newItems = [...mockDataPrompt.generated_items, response.data];
         onItemsUpdated({ ...mockDataPrompt, generated_items: newItems });
         setNewItemContent('');
         setShowAddForm(false);
     } catch (err) {
         console.error("Error adding new mock item:", err);
         setError(err.response?.data?.detail || err.message || "Failed to add item.");
     } finally {
         setIsLoading(false);
     }
  };

  return (
    <div className="mt-6">
      <div className="flex justify-between items-center mb-3">
        <h4 className="text-lg font-semibold text-green-400">
          Curate Mock Data Items for Prompt ID: {mockDataPrompt.id} 
          ({mockDataPrompt.generated_items?.length || 0} items)
        </h4>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-3 py-1 text-sm bg-green-600 hover:bg-green-700 text-white rounded"
        >
          {showAddForm ? 'Cancel Add' : '+ Add New Item'}
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={handleAddNewItem} className="mb-4 p-3 bg-gray-750 rounded">
          <h5 className="text-md font-semibold text-gray-200 mb-2">Add New Mock Item</h5>
          <textarea
            rows="5"
            value={newItemContent}
            onChange={(e) => setNewItemContent(e.target.value)}
            className="w-full p-2 bg-gray-900 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-xs text-white"
            placeholder='{ "new_key": "new_value" }'
          />
          <button
            type="submit"
            disabled={isLoading || !newItemContent.trim()}
            className="mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md disabled:opacity-50"
          >
            {isLoading ? 'Adding...' : 'Save New Item'}
          </button>
          {error && <p className="mt-1 text-xs text-red-400">Error: {error}</p>}
        </form>
      )}

      <div className="max-h-96 overflow-y-auto space-y-2 border border-gray-700 p-2 rounded">
        {mockDataPrompt.generated_items && mockDataPrompt.generated_items.length > 0 ? (
          mockDataPrompt.generated_items.map((item) => (
            <MockDataItem
              key={item.id}
              item={item}
              promptId={mockDataPrompt.id}
              onUpdate={handleUpdateItemInList}
              onDelete={handleDeleteItemInList}
            />
          ))
        ) : (
          <p className="text-gray-500 text-center py-4">No mock data items to display for this prompt.</p>
        )}
      </div>
      {error && !showAddForm && <p className="mt-4 text-red-400">Error: {error}</p>}
    </div>
  );
};

export default MockDataManagement;