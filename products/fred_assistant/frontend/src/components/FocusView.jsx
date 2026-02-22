import { useState, useEffect, useRef } from 'react';
import { Timer, Play, Square, BarChart3 } from 'lucide-react';
import { fetchTodayTasks } from '../api';
import {
  startFocus, stopFocus, fetchActiveSession, fetchFocusStats, fetchFocusSessions,
} from '../api';

const PRESETS = [25, 50, 90];

export default function FocusView() {
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState('');
  const [minutes, setMinutes] = useState(25);
  const [active, setActive] = useState(null);
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [timeLeft, setTimeLeft] = useState(0);
  const timerRef = useRef(null);

  const load = async () => {
    const [t, a, s, h] = await Promise.allSettled([
      fetchTodayTasks(), fetchActiveSession(), fetchFocusStats(), fetchFocusSessions(),
    ]);
    if (t.status === 'fulfilled') setTasks(t.value);
    if (a.status === 'fulfilled' && a.value && a.value.id) {
      setActive(a.value);
      const start = new Date(a.value.started_at);
      const end = new Date(start.getTime() + a.value.planned_minutes * 60000);
      const left = Math.max(0, Math.floor((end - Date.now()) / 1000));
      setTimeLeft(left);
    }
    if (s.status === 'fulfilled') setStats(s.value);
    if (h.status === 'fulfilled') setSessions(h.value);
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (active && timeLeft > 0) {
      timerRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) { clearInterval(timerRef.current); return 0; }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timerRef.current);
    }
  }, [active, timeLeft]);

  const handleStart = async () => {
    const result = await startFocus(selectedTask || undefined, minutes);
    if (result && result.id) {
      setActive(result);
      setTimeLeft(minutes * 60);
    }
  };

  const handleStop = async (completed = true) => {
    if (!active) return;
    await stopFocus(active.id, completed);
    clearInterval(timerRef.current);
    setActive(null);
    setTimeLeft(0);
    load();
  };

  const fmt = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Timer size={14} className="text-orange-400" />
        <span className="text-xs font-semibold text-gray-300">Focus Mode</span>
      </div>

      {/* Timer */}
      <div className="card p-6 text-center">
        {active ? (
          <>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Focusing on</div>
            <div className="text-sm font-medium mb-3">{active.task_title || 'Deep work'}</div>
            <div className="text-5xl font-mono font-bold text-orange-400 mb-4">{fmt(timeLeft)}</div>
            <div className="flex justify-center gap-2">
              <button onClick={() => handleStop(true)} className="btn-primary text-xs px-4 py-2 flex items-center gap-1">
                <Square size={12} /> Complete
              </button>
              <button onClick={() => handleStop(false)} className="btn-ghost text-xs px-4 py-2 text-red-400">
                Cancel
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-3">Start a Focus Session</div>
            <select
              value={selectedTask}
              onChange={(e) => setSelectedTask(e.target.value)}
              className="input text-xs w-full max-w-xs mx-auto mb-3"
            >
              <option value="">No specific task (deep work)</option>
              {tasks.filter((t) => t.status !== 'done').map((t) => (
                <option key={t.id} value={t.id}>{t.title}</option>
              ))}
            </select>
            <div className="flex justify-center gap-2 mb-4">
              {PRESETS.map((p) => (
                <button
                  key={p}
                  onClick={() => setMinutes(p)}
                  className={`text-xs px-3 py-1 rounded-lg ${minutes === p ? 'bg-orange-500/20 text-orange-400' : 'bg-white/5 text-gray-500 hover:text-gray-300'}`}
                >
                  {p}min
                </button>
              ))}
            </div>
            <button onClick={handleStart} className="btn-primary text-xs px-6 py-2 flex items-center gap-1 mx-auto">
              <Play size={12} /> Start Focus ({minutes}min)
            </button>
          </>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="card p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <BarChart3 size={11} className="text-orange-400" />
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Focus Stats (7 days)</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <div className="text-lg font-bold text-orange-400">{stats.total_minutes}</div>
              <div className="text-[10px] text-gray-600">Minutes</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold">{stats.total_sessions}</div>
              <div className="text-[10px] text-gray-600">Sessions</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold">{stats.avg_duration}</div>
              <div className="text-[10px] text-gray-600">Avg Min</div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Sessions */}
      {sessions.length > 0 && (
        <div>
          <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Recent Sessions</h4>
          <div className="space-y-1">
            {sessions.slice(0, 10).map((s) => (
              <div key={s.id} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02]">
                <div>
                  <span className="text-xs">{s.task_title || 'Deep work'}</span>
                  <div className="text-[10px] text-gray-600">{s.started_at?.slice(0, 16)}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-500">{s.planned_minutes}min</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${s.completed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-500/20 text-gray-400'}`}>
                    {s.completed ? 'done' : 'cancelled'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
