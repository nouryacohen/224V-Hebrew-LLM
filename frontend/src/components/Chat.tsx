import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

type UserSetup = {
  username: string;
  roleplay?: string;
}

interface ChatProps {
  userSetup: UserSetup;
}

const Chat: React.FC<ChatProps> = ({ userSetup }) => {
  const [messages, setMessages] = useState<Array<{type: string, content: string}>>([]);
  const [input, setInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setMessages(prev => [...prev, { type: 'user', content: input }]);

    try {
      const response = await fetch('http://localhost:8000/converse/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: userSetup.username,
          user_message: input,
          role_play: userSetup.roleplay || null
        })
      });

      const data = await response.json();
      setMessages(prev => [...prev, { type: 'assistant', content: data.response }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        type: 'assistant', 
        content: 'Sorry, there was an error processing your message.' 
      }]);
    }

    setInput('');
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-4 rounded-lg ${
                message.type === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-900'
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t">
        <div className="flex space-x-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Type your message..."
          />
          <button
            type="submit"
            className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700"
          >
            <Send className="w-6 h-6" />
          </button>
        </div>
      </form>
    </div>
  );
};

export default Chat;