import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, Upload, LogOut, 
  Database, AlertCircle, CheckCircle, 
  Download, Send, Bot, User, Play, Loader2, X, Link as LinkIcon
} from 'lucide-react';
import Login from './components/Login';
import SqlVisualizer from './components/SqlVisualizer';
import { AppView, TableSchema, ChatMessage, QueryResult } from './types';
import { loadTableFromCSV, executeSQL } from './services/dbService';
import { GeminiService } from './services/geminiService';
import { SAMPLE_CSV_DATA_1, SAMPLE_CSV_DATA_2 } from './constants';

const App: React.FC = () => {
  const [view, setView] = useState<AppView>(AppView.LOGIN);
  const [username, setUsername] = useState<string>('');
  
  const [tables, setTables] = useState<TableSchema[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState<string>('');
  const [showKaggleModal, setShowKaggleModal] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const geminiRef = useRef<GeminiService | null>(null);

  const handleLogin = (user: string) => {
    setUsername(user);
    geminiRef.current = new GeminiService();
    setView(AppView.DASHBOARD);
    
    // Welcome message
    addMessage({
      role: 'assistant',
      content: `Welcome back, ${user}. I'm ready to analyze your data. Please upload a CSV file or use the sample data to get started.`,
      type: 'text'
    });
  };

  const addMessage = (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    setMessages(prev => [...prev, {
      ...msg,
      id: Math.random().toString(36).substring(7),
      timestamp: Date.now()
    }]);
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const processFile = async (file: File) => {
    try {
      setIsLoading(true);
      setLoadingStep(`Reading ${file.name}...`);
      
      const text = await file.text();
      
      setLoadingStep('Parsing CSV & Building Database...');
      // Give UI a moment to update
      await new Promise(r => setTimeout(r, 100));

      const tableName = file.name.replace('.csv', '').replace(/\s+/g, '_');
      const schema = await loadTableFromCSV(tableName, text);
      
      setTables(prev => [...prev, schema]);
      addMessage({
        role: 'system',
        content: `Successfully loaded table: "${schema.tableName}" with ${schema.rowCount} rows.`,
        type: 'text'
      });
    } catch (error: any) {
      console.error(error);
      addMessage({
        role: 'system',
        content: `Error loading file: ${error.message}`,
        type: 'error'
      });
    } finally {
      setIsLoading(false);
      setLoadingStep('');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) await processFile(file);
    // Reset input
    e.target.value = '';
  };

  const loadSampleData = async () => {
    try {
      setIsLoading(true);
      setLoadingStep('Loading samples...');
      
      // Check if already loaded
      if (tables.some(t => t.tableName === 'Student_Marks_1')) {
        addMessage({ role: 'system', content: "Sample data is already loaded.", type: 'text' });
        setIsLoading(false);
        setLoadingStep('');
        return;
      }

      const s1 = await loadTableFromCSV('Student_Marks_1', SAMPLE_CSV_DATA_1);
      const s2 = await loadTableFromCSV('Student_Marks_2', SAMPLE_CSV_DATA_2);
      setTables(prev => [...prev, s1, s2]);
      addMessage({
        role: 'system',
        content: `Loaded 2 sample datasets. You can now ask questions like "Show students with more than 85% in 10th grade".`,
        type: 'text'
      });
    } catch (e: any) {
      console.error(e);
      addMessage({ role: 'system', content: `Error loading samples: ${e.message}`, type: 'error' });
    } finally {
      setIsLoading(false);
      setLoadingStep('');
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    if (tables.length === 0) {
      addMessage({ role: 'system', content: "Please upload a dataset or load samples first.", type: 'error' });
      return;
    }

    const userQuery = input;
    setInput('');
    setIsLoading(true);
    setLoadingStep('Analyzing schema...');

    // Add User Message
    addMessage({ role: 'user', content: userQuery, type: 'text' });

    try {
      if (!geminiRef.current) throw new Error("Gemini Service not initialized");

      // 1. Generate SQL
      setLoadingStep('Generating SQL via Gemini...');
      const aiResponse = await geminiRef.current.generateSQL(userQuery, tables);
      
      const { sql, explanation } = aiResponse;

      // 2. Execute SQL
      setLoadingStep('Executing Query...');
      const result = executeSQL(sql);

      // 3. Add Result Message
      if (result.error) {
         addMessage({
           role: 'assistant',
           content: explanation,
           type: 'error',
           sql: sql,
           explanation: `Error: ${result.error}` 
         });
      } else {
        addMessage({
          role: 'assistant',
          content: explanation, 
          type: 'sql_result',
          sql: sql,
          data: result.data,
          explanation: explanation
        });
      }

    } catch (error: any) {
      addMessage({ role: 'assistant', content: `Processing Failed: ${error.message}`, type: 'error' });
    } finally {
      setIsLoading(false);
      setLoadingStep('');
    }
  };

  // --- Components ---

  const KaggleModal = () => {
    const [datasetId, setDatasetId] = useState('');
    
    if (!showKaggleModal) return null;

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
        <div className="bg-slate-800 border border-slate-700 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden">
          <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-900/50">
             <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Download className="w-5 h-5 text-blue-400" />
                Import from Kaggle
             </h3>
             <button onClick={() => setShowKaggleModal(false)} className="text-slate-400 hover:text-white transition-colors">
                <X className="w-6 h-6" />
             </button>
          </div>
          
          <div className="p-6 space-y-6">
             <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">1. Enter Kaggle Dataset ID</label>
                <div className="flex gap-2">
                   <input 
                     type="text" 
                     value={datasetId}
                     onChange={(e) => setDatasetId(e.target.value)}
                     placeholder="e.g. heeraldedhia/groceries-dataset"
                     className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
                   />
                   <a 
                     href={datasetId ? `https://www.kaggle.com/datasets/${datasetId}` : '#'}
                     target="_blank"
                     rel="noreferrer"
                     className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        datasetId 
                        ? 'bg-blue-600 hover:bg-blue-500 text-white' 
                        : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                     }`}
                   >
                      <LinkIcon className="w-4 h-4" />
                      Open
                   </a>
                </div>
                <p className="text-xs text-slate-500">
                   Due to browser security (CORS), we cannot auto-download. Please open the link, download the CSV, and drop it below.
                </p>
             </div>

             <div className="relative border-2 border-dashed border-slate-700 bg-slate-900/50 rounded-xl p-8 text-center hover:border-blue-500/50 transition-colors group">
                 <input 
                   type="file" 
                   accept=".csv"
                   className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                   onChange={(e) => {
                      if(e.target.files?.[0]) {
                         processFile(e.target.files[0]);
                         setShowKaggleModal(false);
                      }
                   }}
                 />
                 <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center group-hover:scale-110 transition-transform">
                       <Upload className="w-6 h-6 text-slate-400 group-hover:text-blue-400" />
                    </div>
                    <p className="text-sm font-medium text-slate-300">Drop your Kaggle CSV here</p>
                    <p className="text-xs text-slate-500">or click to browse</p>
                 </div>
             </div>
          </div>
        </div>
      </div>
    );
  };

  const renderMessage = (msg: ChatMessage) => (
    <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''} mb-8 animate-in fade-in slide-in-from-bottom-2 duration-300`}>
      <div className={`w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center shadow-lg ${
        msg.role === 'user' ? 'bg-primary text-white' : 
        msg.role === 'system' ? 'bg-slate-700 text-slate-300' : 
        'bg-gradient-to-br from-indigo-600 to-violet-600 text-white'
      }`}>
        {msg.role === 'user' ? <User className="w-6 h-6" /> : 
         msg.role === 'system' ? <Terminal className="w-5 h-5" /> :
         <Bot className="w-6 h-6" />}
      </div>

      <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
        <div className={`px-5 py-4 rounded-2xl shadow-sm border ${
          msg.role === 'user' ? 'bg-slate-800 text-white border-slate-700 rounded-tr-none' : 
          msg.role === 'system' ? 'bg-slate-800/50 text-slate-400 text-sm border-slate-800 font-mono' :
          'bg-slate-800 text-slate-200 border-slate-700 rounded-tl-none'
        }`}>
          <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

          {msg.sql && (
            <div className="mt-4 bg-slate-950 rounded-lg border border-slate-800 overflow-hidden">
               <div className="bg-slate-900/50 px-3 py-1.5 border-b border-slate-800 flex items-center gap-2">
                 <Database className="w-3 h-3 text-slate-500" />
                 <span className="text-xs text-slate-500 font-mono">Generated SQL</span>
               </div>
               <pre className="p-3 text-sm text-green-400 font-mono overflow-x-auto">
                 <code>{msg.sql}</code>
               </pre>
            </div>
          )}

          {msg.type === 'error' && msg.explanation && (
             <div className="mt-2 text-red-400 text-sm flex items-start gap-2">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{msg.explanation}</span>
             </div>
          )}
        </div>

        {msg.type === 'sql_result' && msg.data && msg.data.length > 0 && (
          <div className="mt-4 w-full overflow-hidden rounded-xl border border-slate-700 shadow-xl bg-slate-800">
            <div className="overflow-x-auto max-h-96 custom-scrollbar">
              <table className="w-full text-sm text-left text-slate-300">
                <thead className="text-xs text-slate-400 uppercase bg-slate-900/50 sticky top-0">
                  <tr>
                    {Object.keys(msg.data[0]).map((key) => (
                      <th key={key} className="px-6 py-3 font-medium whitespace-nowrap">{key}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {msg.data.map((row: any, idx: number) => (
                    <tr key={idx} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                      {Object.values(row).map((val: any, i) => (
                        <td key={i} className="px-6 py-3 whitespace-nowrap">
                          {val?.toString() || '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="bg-slate-900/50 px-4 py-2 text-xs text-slate-500 border-t border-slate-800">
               {msg.data.length} results found
            </div>
          </div>
        )}

        {msg.type === 'sql_result' && msg.data && (
           <SqlVisualizer result={{ data: msg.data, columns: Object.keys(msg.data[0] || {}), sql: msg.sql || '' }} />
        )}
        
        <div className="mt-1 text-xs text-slate-600 ml-1">
          {new Date(msg.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );

  if (view === AppView.LOGIN) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 overflow-hidden font-sans">
      <KaggleModal />
      
      {/* Sidebar */}
      <aside className="hidden md:flex w-72 flex-col bg-slate-900 border-r border-slate-800 z-20">
        <div className="p-6 border-b border-slate-800">
           <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-tr from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                 <Database className="w-5 h-5 text-white" />
              </div>
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">DataHub</span>
           </h2>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-8">
           <div>
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4 px-2">Data Sources</h3>
              <div className="space-y-2">
                 <button 
                   onClick={() => document.getElementById('csv-upload')?.click()}
                   className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-slate-300 rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700 transition-all group"
                 >
                    <Upload className="w-4 h-4 text-slate-500 group-hover:text-primary" />
                    Upload CSV
                    <input id="csv-upload" type="file" accept=".csv" onChange={handleFileUpload} className="hidden" />
                 </button>
                 
                 <button 
                   onClick={() => setShowKaggleModal(true)}
                   className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-slate-300 rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700 transition-all group"
                 >
                    <Download className="w-4 h-4 text-slate-500 group-hover:text-primary" />
                    Import from Kaggle
                 </button>

                 <button 
                   onClick={loadSampleData}
                   className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-slate-300 rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700 transition-all group"
                 >
                    <Play className="w-4 h-4 text-slate-500 group-hover:text-primary" />
                    Load Sample Data
                 </button>
              </div>
           </div>

           <div>
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4 px-2 flex justify-between items-center">
                 <span>Active Tables</span>
                 <span className="bg-slate-800 text-slate-400 text-[10px] px-1.5 py-0.5 rounded-md">{tables.length}</span>
              </h3>
              <div className="space-y-1">
                 {tables.length === 0 ? (
                    <div className="px-3 py-4 text-center border-2 border-dashed border-slate-800 rounded-xl">
                       <p className="text-xs text-slate-600">No tables loaded</p>
                    </div>
                 ) : (
                    tables.map(t => (
                       <div key={t.tableName} className="group flex items-center justify-between px-3 py-2 text-sm text-slate-400 rounded-lg hover:bg-slate-800 transition-colors">
                          <div className="flex items-center gap-2 overflow-hidden">
                             <Database className="w-3.5 h-3.5 text-slate-600 group-hover:text-accent" />
                             <span className="truncate" title={t.tableName}>{t.tableName}</span>
                          </div>
                          <span className="text-[10px] text-slate-600 group-hover:text-slate-500">{t.rowCount} rows</span>
                       </div>
                    ))
                 )}
              </div>
           </div>
        </div>

        <div className="p-4 border-t border-slate-800">
           <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-slate-800 transition-colors cursor-pointer group">
              <div className="w-9 h-9 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 font-semibold group-hover:bg-primary group-hover:text-white transition-colors">
                 {username.slice(0, 2).toUpperCase()}
              </div>
              <div className="flex-1 overflow-hidden">
                 <p className="text-sm font-medium text-slate-200 truncate">{username}</p>
                 <p className="text-xs text-slate-500 truncate">Connected</p>
              </div>
              <button onClick={() => setView(AppView.LOGIN)} title="Logout">
                 <LogOut className="w-4 h-4 text-slate-500 hover:text-white" />
              </button>
           </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative h-full">
         <header className="md:hidden flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/95 backdrop-blur z-10">
            <h1 className="text-lg font-bold text-white">DataHub</h1>
            <button onClick={() => setView(AppView.LOGIN)}>
               <LogOut className="w-5 h-5 text-slate-400" />
            </button>
         </header>

         <div className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth custom-scrollbar">
            <div className="max-w-4xl mx-auto">
               {messages.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-[60vh] text-center opacity-0 animate-in fade-in duration-700">
                     <div className="w-20 h-20 bg-slate-800 rounded-3xl flex items-center justify-center mb-6 shadow-2xl shadow-primary/10">
                        <Bot className="w-10 h-10 text-primary" />
                     </div>
                     <h2 className="text-2xl font-bold text-white mb-2">How can I help you today?</h2>
                     <p className="text-slate-400 max-w-md">
                        Upload your CSV data and ask me anything. I can write SQL, query your data, and visualize the results.
                     </p>
                     
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-8 w-full max-w-lg">
                        {["Show top 5 students by marks", "Count users by gender", "Average score per company"].map((q) => (
                           <button 
                             key={q}
                             onClick={() => setInput(q)} 
                             className="px-4 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-sm text-slate-300 text-left transition-all hover:scale-[1.02]"
                           >
                              {q}
                           </button>
                        ))}
                     </div>
                  </div>
               )}
               
               {messages.map(renderMessage)}
               
               {isLoading && (
                  <div className="flex items-center gap-3 text-slate-500 ml-14 animate-pulse">
                     <Loader2 className="w-4 h-4 animate-spin" />
                     <span className="text-sm font-medium">{loadingStep || 'Thinking...'}</span>
                  </div>
               )}
               
               <div ref={messagesEndRef} className="h-4" />
            </div>
         </div>

         <div className="p-4 md:p-6 bg-slate-900/95 backdrop-blur-sm border-t border-slate-800 z-10">
            <div className="max-w-4xl mx-auto relative">
               <form onSubmit={handleSendMessage} className="relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-accent rounded-2xl opacity-20 group-hover:opacity-40 transition duration-500 blur"></div>
                  <div className="relative flex items-center bg-slate-950 rounded-xl border border-slate-800 shadow-xl overflow-hidden">
                     <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask a question about your data..."
                        disabled={isLoading || tables.length === 0}
                        className="flex-1 bg-transparent text-white px-5 py-4 focus:outline-none placeholder:text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                     />
                     <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="mr-2 p-2.5 bg-primary hover:bg-blue-600 text-white rounded-lg disabled:opacity-50 disabled:hover:bg-primary transition-all shadow-lg shadow-blue-500/20"
                     >
                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                     </button>
                  </div>
               </form>
               <div className="mt-3 flex justify-between items-center px-1">
                  <p className="text-[10px] text-slate-500 font-medium tracking-wide uppercase">
                     Powered by Gemini 2.5 Flash & AlaSQL
                  </p>
                  <p className="text-[10px] text-slate-600">
                     {tables.length > 0 ? `${tables.length} tables active` : 'No data loaded'}
                  </p>
               </div>
            </div>
         </div>
      </main>
    </div>
  );
};

export default App;