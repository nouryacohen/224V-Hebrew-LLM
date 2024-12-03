import React, { useState } from 'react';
import { Send } from 'lucide-react';

type Message = {
  type: 'user' | 'assistant';
  content: string;
  wordsAffected?: string[];
  mastery?: Record<string, number>;
};

interface SidebarProps {
  userSetup: UserSetup;
}

const Sidebar: React.FC<SidebarProps> = ({ userSetup }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setMessages(prev => [...prev, { type: 'user', content: input }]);

    try {
      const response = await fetch('http://localhost:8000/assist/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: input,
          username: userSetup.username 
        })
      });

      const data = await response.json();
      setMessages(prev => [...prev, { 
        type: 'assistant', 
        content: data.response,
        wordsAffected: data.words_affected,
        mastery: data.updated_mastery
      }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        type: 'assistant', 
        content: 'Sorry, there was an error processing your question.' 
      }]);
    }

    setInput('');
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold">Hebrew Assistant</h2>
        <p className="text-sm text-gray-600">Ask questions about Hebrew language</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div key={index} className="space-y-2">
            <div
              className={`${
                message.type === 'user' 
                  ? 'ml-auto bg-indigo-600 text-white' 
                  : 'mr-auto bg-white'
              } max-w-[90%] p-3 rounded-lg shadow-sm`}
            >
              {message.content}
            </div>
            {message.wordsAffected && message.wordsAffected.length > 0 && (
              <div className="text-sm text-gray-600 p-2 bg-gray-100 rounded">
                <p>Words detected:</p>
                {message.wordsAffected.map((word) => (
                  <div key={word} className="flex justify-between">
                    <span>{word}</span>
                    <span>Mastery: {(message.mastery?.[word] || 0) * 100}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about Hebrew..."
            className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  );
};

export default Sidebar;