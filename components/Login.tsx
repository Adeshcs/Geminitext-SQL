import React, { useState } from 'react';
import { Database, User as UserIcon } from 'lucide-react';

interface LoginProps {
  onLogin: (username: string) => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username) {
      setError('Please enter a username');
      return;
    }
    onLogin(username);
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative">
      {/* Background Image with Overlay */}
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center"
        style={{ backgroundImage: 'url("https://picsum.photos/1920/1080?grayscale&blur=2")' }}
      ></div>
      <div className="absolute inset-0 bg-slate-900/80 z-0"></div>

      <div className="relative z-10 w-full max-w-md p-8 bg-slate-800/90 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-700">
        <div className="flex flex-col items-center mb-8">
          <div className="p-4 bg-primary/20 rounded-full mb-4">
            <Database className="w-10 h-10 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-white">Gemini Text-to-SQL</h1>
          <p className="text-slate-400 mt-2 text-center">Enterprise Data Intelligence</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-200 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300 ml-1">Username</label>
            <div className="relative">
              <UserIcon className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-700 text-white rounded-xl py-2.5 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                placeholder="Enter your name"
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full bg-gradient-to-r from-primary to-accent hover:from-blue-600 hover:to-violet-600 text-white font-bold py-3 rounded-xl transition-all transform hover:scale-[1.02] shadow-lg shadow-primary/25"
          >
            Access Platform
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;