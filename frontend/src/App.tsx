import { useState } from 'react'
import Chat from './components/Chat'
import Sidebar from './components/Sidebar'

export type UserSetup = {
  username: string;
  roleplay?: string;
}

function App() {
  const [userSetup, setUserSetup] = useState<UserSetup | null>(null);
  const [username, setUsername] = useState('');
  const [roleplay, setRoleplay] = useState('');

  const handleSetup = (e: React.FormEvent) => {
    e.preventDefault();
    if (username) {
      setUserSetup({ username, roleplay: roleplay || undefined });
    }
  };

  if (!userSetup) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="p-8 bg-white rounded-lg shadow-md w-96">
          <h2 className="text-2xl font-bold mb-4">Setup Your Learning Profile</h2>
          <form onSubmit={handleSetup} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Roleplay Character (optional)</label>
              <input
                type="text"
                value={roleplay}
                onChange={(e) => setRoleplay(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                placeholder="e.g., Harry Potter"
              />
            </div>
            <button
              type="submit"
              className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700"
            >
              Start Learning
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex">
      <div className="flex-1">
        <Chat userSetup={userSetup} />
      </div>
      <div className="w-96 border-l border-gray-200">
        <Sidebar userSetup={userSetup} />
      </div>
    </div>
  )
}

export default App