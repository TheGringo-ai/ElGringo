import { useState, useEffect, useCallback } from 'react';
import { LayoutDashboard, Brain, MessageCircle } from 'lucide-react';
import { fetchStats, fetchBoards } from './api';
import QuickCapture from './components/QuickCapture';
import StatsBar from './components/StatsBar';
import TodayView from './components/TodayView';
import BoardView from './components/BoardView';
import ChatPanel from './components/ChatPanel';
import MemoryPanel from './components/MemoryPanel';

const NAV = [
  { id: 'today', label: 'Today', icon: LayoutDashboard },
  { id: 'chat', label: 'Fred', icon: MessageCircle },
  { id: 'memory', label: 'Memory', icon: Brain },
];

export default function App() {
  const [stats, setStats] = useState(null);
  const [boards, setBoards] = useState([]);
  const [view, setView] = useState('today');
  const [activeBoard, setActiveBoard] = useState(null);

  const loadAll = useCallback(async () => {
    const [s, b] = await Promise.allSettled([fetchStats(), fetchBoards()]);
    if (s.status === 'fulfilled') setStats(s.value);
    if (b.status === 'fulfilled') setBoards(b.value);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Auto-refresh every 30s
  useEffect(() => {
    const id = setInterval(loadAll, 30000);
    return () => clearInterval(id);
  }, [loadAll]);

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className="h-screen flex flex-col bg-surface-900 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-white/10">
        <div>
          <h1 className="text-base font-semibold">
            {greeting()}, Fred
          </h1>
          <p className="text-[11px] text-gray-500">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <StatsBar stats={stats} />
      </header>

      {/* Quick Capture */}
      <div className="px-5 py-2 border-b border-white/5">
        <QuickCapture onCreated={loadAll} />
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Nav */}
        <nav className="w-[200px] flex-shrink-0 border-r border-white/10 p-3 flex flex-col gap-1 overflow-y-auto">
          {NAV.map((item) => (
            <button
              key={item.id}
              onClick={() => { setView(item.id); setActiveBoard(null); }}
              className={`flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                view === item.id && !activeBoard
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
              }`}
            >
              <item.icon size={14} />
              {item.label}
            </button>
          ))}

          <div className="mt-4 mb-1 px-3">
            <span className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider">Boards</span>
          </div>
          {boards.map((board) => (
            <button
              key={board.id}
              onClick={() => { setActiveBoard(board); setView('board'); }}
              className={`flex items-center justify-between w-full text-left px-3 py-1.5 rounded-lg text-xs transition-colors ${
                activeBoard?.id === board.id
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
              }`}
            >
              <span className="flex items-center gap-2">
                <span>{board.icon}</span>
                {board.name}
              </span>
              {board.task_count > 0 && (
                <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 rounded-full">{board.task_count}</span>
              )}
            </button>
          ))}
        </nav>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-5">
          {view === 'today' && !activeBoard && <TodayView onRefresh={loadAll} />}
          {view === 'chat' && !activeBoard && <ChatPanel />}
          {view === 'memory' && !activeBoard && <MemoryPanel />}
          {activeBoard && <BoardView board={activeBoard} onRefresh={loadAll} />}
        </main>
      </div>
    </div>
  );
}
