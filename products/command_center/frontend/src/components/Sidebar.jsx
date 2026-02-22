import { useState, useEffect } from 'react';
import { RefreshCw, Loader2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchTodayStandup, generateStandup } from '../api/automation';
import { fetchVelocity } from '../api/sprints';
import SchedulerList from './SchedulerList';

export default function Sidebar({ scheduler, onRefresh }) {
  const [standup, setStandup] = useState(null);
  const [velocity, setVelocity] = useState([]);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    fetchTodayStandup().then(setStandup).catch(() => {});
    fetchVelocity(4).then(setVelocity).catch(() => {});
  }, []);

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const result = await generateStandup();
      setStandup(result);
    } catch { /* noop */ }
    setRegenerating(false);
  };

  return (
    <aside className="w-[280px] flex-shrink-0 border-l border-white/10 p-4 overflow-y-auto space-y-5">
      {/* Automation */}
      <section>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Automation
        </h3>
        <SchedulerList tasks={scheduler} onRefresh={onRefresh} />
      </section>

      {/* Today's Standup */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Today's Standup
          </h3>
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="p-1 hover:bg-white/10 rounded text-gray-600 hover:text-gray-400 disabled:opacity-40"
            title="Regenerate"
          >
            {regenerating ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          </button>
        </div>
        {standup?.formatted ? (
          <div className="text-xs text-gray-400 leading-relaxed whitespace-pre-wrap bg-white/[0.03] rounded-lg p-3 border border-white/5">
            {standup.formatted}
          </div>
        ) : (
          <div className="text-xs text-gray-700 text-center py-4">No standup generated yet</div>
        )}
      </section>

      {/* Velocity Chart */}
      <section>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Velocity
        </h3>
        {velocity.length > 0 ? (
          <div className="h-[120px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={velocity}>
                <XAxis
                  dataKey="sprint"
                  tick={{ fontSize: 10, fill: '#4b5563' }}
                  axisLine={{ stroke: '#1f2937' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#4b5563' }}
                  axisLine={false}
                  tickLine={false}
                  width={30}
                />
                <Tooltip
                  contentStyle={{
                    background: '#1a1a25',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#9ca3af',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="velocity"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#3b82f6' }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="completion"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#8b5cf6' }}
                  activeDot={{ r: 5 }}
                  strokeDasharray="4 4"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="text-xs text-gray-700 text-center py-4">No velocity data</div>
        )}
      </section>
    </aside>
  );
}
