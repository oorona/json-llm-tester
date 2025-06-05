// frontend/src/components/MockDataItem.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = '';

const MockDataItem = ({ item, promptId, onUpdate, onDelete }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editableContent, setEditableContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setEditableContent(JSON.stringify(item.item_content, null, 2));
  }, [item.item_content]);

  const handleSave = async () => {
    let parsedContent;
    try {
      parsedContent = JSON.parse(editableContent);
    } catch (e) {
      setError("Invalid JSON format.");
      return;
    }
    setIsLoading(true); setError(null);
    try {
      const response = await axios.put(`${API_BASE_URL}/mock-data/items/${item.id}`, {
        item_content: parsedContent,
      });
      onUpdate(response.data); // Pass updated item back to parent
      setIsEditing(false);
    } catch (err) {
      console.error("Error updating mock data item:", err);
      setError(err.response?.data?.detail || err.message || "Failed to update item.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this mock data item?")) return;
    setIsLoading(true); setError(null);
    try {
      await axios.delete(`${API_BASE_URL}/mock-data/items/${item.id}`);
      onDelete(item.id); // Notify parent to remove from list
    } catch (err) {
      console.error("Error deleting mock data item:", err);
      setError(err.response?.data?.detail || err.message || "Failed to delete item.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-3 bg-gray-700 rounded mb-2 shadow">
      <div className="flex justify-between items-start">
        <h5 className="text-xs font-semibold text-gray-300 mb-1">Item ID: {item.id} (Prompt ID: {item.prompt_id})</h5>
        <div>
          <button
            onClick={() => setIsEditing(!isEditing)}
            className={`px-2 py-1 text-xs rounded mr-1 ${isEditing ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-blue-600 hover:bg-blue-700'} text-white`}
          >
            {isEditing ? 'Cancel Edit' : 'Edit'}
          </button>
          {!isEditing && (
             <button
                 onClick={handleDelete}
                 disabled={isLoading}
                 className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded disabled:opacity-50"
             >
                 Delete
             </button>
          )}
        </div>
      </div>

      {isEditing ? (
        <div>
          <textarea
            rows="5"
            value={editableContent}
            onChange={(e) => setEditableContent(e.target.value)}
            className="w-full p-2 mt-1 bg-gray-900 border border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-xs text-white"
          />
          <button
            onClick={handleSave}
            disabled={isLoading}
            className="mt-2 px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white font-semibold rounded-md disabled:opacity-50"
          >
            {isLoading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      ) : (
        <pre className="mt-1 text-xs whitespace-pre-wrap text-gray-200">{JSON.stringify(item.item_content, null, 2)}</pre>
      )}
      {error && <p className="mt-1 text-xs text-red-400">Error: {error}</p>}
    </div>
  );
};

export default MockDataItem;