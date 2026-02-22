import { useState, useEffect, useCallback } from 'react';
import { PanelLeftClose, PanelLeft } from 'lucide-react';
import { fetchStats, fetchCurrentSprint } from './api/sprints';
import { fetchTasks, updateTaskStatus } from './api/sprints';
import { fetchContent } from './api/content';
import { fetchScheduler } from './api/automation';
import MetricsStrip from './components/MetricsStrip';
import SprintBoard from './components/SprintBoard';
import ContentQueue from './components/ContentQueue';
import ChatPanel from './components/ChatPanel';
import Sidebar from './components/Sidebar';
import usePolling from './hooks/usePolling';

export default function App() {
  const [stats, setStats] = useState(null);
  const [sprint, setSprint] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [content, setContent] = useState([]);
  const [scheduler, setScheduler] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedTask, setSelectedTask] = useState(null);

  const loadAll = useCallback(async () => {
    const [statsRes, sprintRes, tasksRes, contentRes, schedulerRes] = await Promise.allSettled([
      fetchStats(),
      fetchCurrentSprint(),
      fetchTasks(),
      fetchContent(),
      fetchScheduler(),
    ]);
    if (statsRes.status === 'fulfilled') setStats(statsRes.value);
    if (sprintRes.status === 'fulfilled') setSprint(sprintRes.value);
    if (tasksRes.status === 'fulfilled') setTasks(tasksRes.value);
    if (contentRes.status === 'fulfilled') setContent(contentRes.value);
    if (schedulerRes.status === 'fulfilled') setScheduler(schedulerRes.value);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);
  usePolling(loadAll, 30000);

  const handleStatusChange = async (taskId, newStatus) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
    );
    try {
      await updateTaskStatus(taskId, newStatus);
      const [newStats, newTasks] = await Promise.all([fetchStats(), fetchTasks()]);
      setStats(newStats);
      setTasks(newTasks);
    } catch {
      loadAll();
    }
  };

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-tight">FredAI Command Center</h1>
          <span className="text-xs text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">
            Founder OS
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">{today}</span>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg hover:bg-white/10 transition-colors text-gray-400"
          >
            {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
          </button>
        </div>
      </header>

      {/* Metrics */}
      <MetricsStrip stats={stats} sprint={sprint} content={content} scheduler={scheduler} />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 flex flex-col overflow-hidden p-4 gap-4">
          {/* Sprint Board + Content Queue */}
          <div className="flex gap-4 flex-1 min-h-0">
            <div className="flex-[7] min-w-0">
              <SprintBoard
                tasks={tasks}
                selectedTask={selectedTask}
                onSelectTask={setSelectedTask}
                onStatusChange={handleStatusChange}
              />
            </div>
            <div className="flex-[5] min-w-0">
              <ContentQueue content={content} onRefresh={loadAll} />
            </div>
          </div>

          {/* Chat Panel */}
          <div className="h-[320px] flex-shrink-0">
            <ChatPanel />
          </div>
        </main>

        {/* Sidebar */}
        {sidebarOpen && (
          <Sidebar scheduler={scheduler} onRefresh={loadAll} />
        )}
      </div>
    </div>
  );
}
