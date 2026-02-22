import { useState, useEffect } from 'react';
import { Calendar, Plus, Trash2, Clock, MapPin, ChevronLeft, ChevronRight } from 'lucide-react';
import { fetchCalendarEvents, createCalendarEvent, deleteCalendarEvent, fetchTodayEvents } from '../api';

const EVENT_COLORS = {
  blue: 'bg-blue-500/20 border-l-blue-400 text-blue-300',
  red: 'bg-red-500/20 border-l-red-400 text-red-300',
  emerald: 'bg-emerald-500/20 border-l-emerald-400 text-emerald-300',
  purple: 'bg-purple-500/20 border-l-purple-400 text-purple-300',
  amber: 'bg-amber-500/20 border-l-amber-400 text-amber-300',
  pink: 'bg-pink-500/20 border-l-pink-400 text-pink-300',
};

const TYPE_LABELS = {
  event: 'Event', meeting: 'Meeting', deadline: 'Deadline',
  timeblock: 'Focus Time', reminder: 'Reminder',
};

function EventCard({ event, onDelete }) {
  const color = EVENT_COLORS[event.color] || EVENT_COLORS.blue;
  return (
    <div className={`p-2 rounded-lg border-l-2 ${color} group animate-slide-up`}>
      <div className="flex items-start justify-between gap-1">
        <span className="text-[11px] font-medium flex-1">{event.title}</span>
        <button onClick={() => onDelete(event.id)}
          className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-600 hover:text-red-400">
          <Trash2 size={10} />
        </button>
      </div>
      <div className="flex items-center gap-2 mt-1">
        {event.start_time && (
          <span className="text-[10px] text-gray-500 flex items-center gap-0.5">
            <Clock size={8} />
            {event.start_time}{event.end_time ? ` - ${event.end_time}` : ''}
          </span>
        )}
        {event.all_day && <span className="text-[10px] text-gray-500">All day</span>}
        {event.location && (
          <span className="text-[10px] text-gray-500 flex items-center gap-0.5">
            <MapPin size={8} />{event.location}
          </span>
        )}
      </div>
      {event.description && (
        <div className="text-[10px] text-gray-600 mt-1 truncate">{event.description}</div>
      )}
    </div>
  );
}

function DayCell({ date, events, isToday, isCurrentMonth, onDelete }) {
  const day = date.getDate();
  return (
    <div className={`min-h-[70px] p-1 border border-white/5 rounded ${
      isToday ? 'bg-blue-500/10 border-blue-500/30' : isCurrentMonth ? '' : 'opacity-40'
    }`}>
      <span className={`text-[10px] font-medium ${
        isToday ? 'text-blue-400' : 'text-gray-500'
      }`}>{day}</span>
      <div className="space-y-0.5 mt-0.5">
        {events.slice(0, 2).map((e) => (
          <div key={e.id} className={`text-[9px] px-1 py-0.5 rounded truncate ${
            EVENT_COLORS[e.color]?.split(' ')[0] || 'bg-blue-500/20'
          } text-gray-300`}>{e.title}</div>
        ))}
        {events.length > 2 && (
          <span className="text-[9px] text-gray-600">+{events.length - 2} more</span>
        )}
      </div>
    </div>
  );
}

export default function CalendarView() {
  const [events, setEvents] = useState([]);
  const [todayEvents, setTodayEvents] = useState([]);
  const [view, setView] = useState('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    title: '', event_type: 'event', start_date: new Date().toISOString().slice(0, 10),
    start_time: '', end_time: '', color: 'blue', location: '', description: '', all_day: false,
  });

  const loadEvents = async () => {
    // Load the whole month
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const start = new Date(year, month, 1).toISOString().slice(0, 10);
    const end = new Date(year, month + 1, 0).toISOString().slice(0, 10);
    const [all, today] = await Promise.allSettled([
      fetchCalendarEvents({ start_date: start, end_date: end }),
      fetchTodayEvents(),
    ]);
    if (all.status === 'fulfilled') setEvents(all.value);
    if (today.status === 'fulfilled') setTodayEvents(today.value);
  };

  useEffect(() => { loadEvents(); }, [currentDate]);

  const handleAdd = async () => {
    if (!form.title.trim()) return;
    await createCalendarEvent(form);
    setForm({ ...form, title: '', start_time: '', end_time: '', location: '', description: '' });
    setShowAdd(false);
    loadEvents();
  };

  const handleDelete = async (id) => {
    setEvents((prev) => prev.filter((e) => e.id !== id));
    setTodayEvents((prev) => prev.filter((e) => e.id !== id));
    await deleteCalendarEvent(id);
  };

  const nav = (dir) => {
    const d = new Date(currentDate);
    d.setMonth(d.getMonth() + dir);
    setCurrentDate(d);
  };

  // Build month grid
  const buildMonthGrid = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    const todayStr = today.toISOString().slice(0, 10);

    const cells = [];
    // Padding days from previous month
    const prevMonthDays = new Date(year, month, 0).getDate();
    for (let i = firstDay - 1; i >= 0; i--) {
      const d = new Date(year, month - 1, prevMonthDays - i);
      cells.push({ date: d, isCurrentMonth: false });
    }
    // Current month
    for (let i = 1; i <= daysInMonth; i++) {
      const d = new Date(year, month, i);
      cells.push({ date: d, isCurrentMonth: true });
    }
    // Padding for next month
    const remaining = 42 - cells.length;
    for (let i = 1; i <= remaining; i++) {
      const d = new Date(year, month + 1, i);
      cells.push({ date: d, isCurrentMonth: false });
    }

    return cells.map((cell) => {
      const dateStr = cell.date.toISOString().slice(0, 10);
      return {
        ...cell,
        isToday: dateStr === todayStr,
        events: events.filter((e) => e.start_date === dateStr),
      };
    });
  };

  const monthGrid = buildMonthGrid();
  const monthName = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar size={14} className="text-emerald-400" />
          <span className="text-xs font-semibold text-gray-300">Calendar</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5">
            {['month', 'agenda'].map((v) => (
              <button key={v} onClick={() => setView(v)}
                className={`text-[10px] px-2 py-0.5 rounded-full ${
                  view === v ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'
                }`}>{v}</button>
            ))}
          </div>
          <button onClick={() => setShowAdd(!showAdd)} className="btn-ghost text-xs py-1 px-2">
            <Plus size={12} />
          </button>
        </div>
      </div>

      {/* Add Event Form */}
      {showAdd && (
        <div className="card p-3 space-y-2">
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Event title..." className="input w-full text-xs" onKeyDown={(e) => e.key === 'Enter' && handleAdd()} />
          <div className="grid grid-cols-2 gap-2">
            <select value={form.event_type} onChange={(e) => setForm({ ...form, event_type: e.target.value })} className="input text-xs">
              {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} className="input text-xs">
              {Object.keys(EVENT_COLORS).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className="input text-xs" />
            <input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} placeholder="Start time" className="input text-xs" />
            <input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} placeholder="End time" className="input text-xs" />
            <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="Location" className="input text-xs" />
          </div>
          <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Description (optional)" className="input w-full text-xs" />
          <button onClick={handleAdd} className="btn-primary text-xs w-full">Add Event</button>
        </div>
      )}

      {/* Month Navigation */}
      {view === 'month' && (
        <>
          <div className="flex items-center justify-between">
            <button onClick={() => nav(-1)} className="btn-ghost p-1"><ChevronLeft size={14} /></button>
            <span className="text-xs font-semibold text-gray-300">{monthName}</span>
            <button onClick={() => nav(1)} className="btn-ghost p-1"><ChevronRight size={14} /></button>
          </div>
          {/* Day headers */}
          <div className="grid grid-cols-7 gap-0.5">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
              <div key={d} className="text-[9px] font-semibold text-gray-600 text-center py-1">{d}</div>
            ))}
            {monthGrid.map((cell, i) => (
              <DayCell key={i} {...cell} onDelete={handleDelete} />
            ))}
          </div>
        </>
      )}

      {/* Agenda View */}
      {view === 'agenda' && (
        <div className="space-y-3">
          {todayEvents.length > 0 && (
            <div>
              <h5 className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider mb-1.5">Today</h5>
              <div className="space-y-1">
                {todayEvents.map((e) => <EventCard key={e.id} event={e} onDelete={handleDelete} />)}
              </div>
            </div>
          )}
          <div>
            <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              {monthName}
            </h5>
            <div className="space-y-1">
              {events.length > 0 ? events.map((e) => (
                <div key={e.id} className="flex gap-2 items-start">
                  <span className="text-[10px] text-gray-600 w-16 flex-shrink-0">{e.start_date.slice(5)}</span>
                  <EventCard event={e} onDelete={handleDelete} />
                </div>
              )) : (
                <div className="text-[11px] text-gray-700 text-center py-4">No events this month</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
