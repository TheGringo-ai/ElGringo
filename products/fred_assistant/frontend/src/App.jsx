import { useState, useEffect, useCallback } from 'react';
import {
  LayoutDashboard, Brain, MessageCircle, FolderGit2,
  Calendar, FileText, TrendingUp, Timer, Users, BarChart3,
  Inbox, BookOpen, Activity, Rocket,
} from 'lucide-react';
import { fetchStats, fetchBoards, fetchInboxCount } from './api';
import QuickCapture from './components/QuickCapture';
import StatsBar from './components/StatsBar';
import TodayView from './components/TodayView';
import BoardView from './components/BoardView';
import ChatPanel from './components/ChatPanel';
import MemoryPanel from './components/MemoryPanel';
import ProjectsView from './components/ProjectsView';
import CalendarView from './components/CalendarView';
import ContentView from './components/ContentView';
import CoachView from './components/CoachView';
import FocusView from './components/FocusView';
import CRMView from './components/CRMView';
import CEOLensView from './components/CEOLensView';
import InboxView from './components/InboxView';
import PlaybookView from './components/PlaybookView';
import UsageView from './components/UsageView';
import FactoryView from './components/FactoryView';

const NAV_GROUPS = [
  { label: 'Productivity', items: [
    { id: 'today', label: 'Today', icon: LayoutDashboard },
    { id: 'inbox', label: 'Inbox', icon: Inbox, badge: true },
    { id: 'focus', label: 'Focus', icon: Timer },
    { id: 'calendar', label: 'Calendar', icon: Calendar },
  ]},
  { label: 'AI', items: [
    { id: 'chat', label: 'Fred', icon: MessageCircle },
    { id: 'coach', label: 'Coach', icon: TrendingUp },
    { id: 'metrics', label: 'CEO Lens', icon: BarChart3 },
  ]},
  { label: 'Projects', items: [
    { id: 'projects', label: 'Projects', icon: FolderGit2 },
    { id: 'content', label: 'Content', icon: FileText },
    { id: 'factory', label: 'App Factory', icon: Rocket },
  ]},
  { label: 'System', items: [
    { id: 'playbooks', label: 'Playbooks', icon: BookOpen },
    { id: 'usage', label: 'AI Usage', icon: Activity },
    { id: 'memory', label: 'Memory', icon: Brain },
    { id: 'crm', label: 'CRM', icon: Users },
  ]},
];

export default function App() {
  const [stats, setStats] = useState(null);
  const [boards, setBoards] = useState([]);
  const [view, setView] = useState('today');
  const [activeBoard, setActiveBoard] = useState(null);
  const [inboxCount, setInboxCount] = useState(0);

  const loadAll = useCallback(async () => {
    const [s, b, ic] = await Promise.allSettled([fetchStats(), fetchBoards(), fetchInboxCount()]);
    if (s.status === 'fulfilled') setStats(s.value);
    if (b.status === 'fulfilled') setBoards(b.value);
    if (ic.status === 'fulfilled') setInboxCount(ic.value?.total || 0);
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
          <p className="text-xs text-gray-500">
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
        <nav className="w-[200px] flex-shrink-0 border-r border-white/10 p-3 flex flex-col overflow-y-auto">
          {NAV_GROUPS.map((group, gi) => (
            <div key={group.label} className={gi > 0 ? 'mt-3' : ''}>
              <div className="mb-1 px-3">
                <span className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider">{group.label}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => { setView(item.id); setActiveBoard(null); }}
                    className={`flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      view === item.id && !activeBoard
                        ? 'bg-white/10 text-white'
                        : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                    }`}
                  >
                    <item.icon size={14} />
                    {item.label}
                    {item.badge && inboxCount > 0 && (
                      <span className="ml-auto text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded-full font-bold">
                        {inboxCount}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}

          <div className="mt-4 mb-1 px-3">
            <span className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Boards</span>
          </div>
          {boards.map((board) => (
            <button
              key={board.id}
              onClick={() => { setActiveBoard(board); setView('board'); }}
              className={`flex items-center justify-between w-full text-left px-3 py-1.5 rounded-lg text-sm transition-colors ${
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
                <span className="text-xs text-gray-600 bg-white/5 px-1.5 rounded-full">{board.task_count}</span>
              )}
            </button>
          ))}
        </nav>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-5">
          {view === 'today' && !activeBoard && <TodayView onRefresh={loadAll} />}
          {view === 'inbox' && !activeBoard && <InboxView />}
          {view === 'focus' && !activeBoard && <FocusView />}
          {view === 'chat' && !activeBoard && <ChatPanel />}
          {view === 'coach' && !activeBoard && <CoachView />}
          {view === 'crm' && !activeBoard && <CRMView />}
          {view === 'metrics' && !activeBoard && <CEOLensView />}
          {view === 'calendar' && !activeBoard && <CalendarView />}
          {view === 'projects' && !activeBoard && <ProjectsView />}
          {view === 'content' && !activeBoard && <ContentView />}
          {view === 'playbooks' && !activeBoard && <PlaybookView />}
          {view === 'factory' && !activeBoard && <FactoryView />}
          {view === 'usage' && !activeBoard && <UsageView />}
          {view === 'memory' && !activeBoard && <MemoryPanel />}
          {activeBoard && <BoardView board={activeBoard} onRefresh={loadAll} />}
        </main>
      </div>
    </div>
  );
}
