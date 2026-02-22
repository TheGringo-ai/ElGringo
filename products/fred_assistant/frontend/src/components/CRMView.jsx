import { useState, useEffect } from 'react';
import { Users, Plus, Phone, Mail, ChevronRight, DollarSign } from 'lucide-react';
import {
  fetchLeads, createLead, updateLead, deleteLead, logOutreach,
  scheduleFollowup, fetchPipeline, fetchFollowups,
} from '../api';

const STAGES = ['cold', 'contacted', 'call_booked', 'trial', 'paid', 'churned'];
const STAGE_COLORS = {
  cold: 'bg-blue-500/20 text-blue-400',
  contacted: 'bg-yellow-500/20 text-yellow-400',
  call_booked: 'bg-orange-500/20 text-orange-400',
  trial: 'bg-purple-500/20 text-purple-400',
  paid: 'bg-emerald-500/20 text-emerald-400',
  churned: 'bg-red-500/20 text-red-400',
};

export default function CRMView() {
  const [leads, setLeads] = useState([]);
  const [pipeline, setPipeline] = useState(null);
  const [filter, setFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [form, setForm] = useState({ name: '', company: '', email: '', source: '', deal_value: 0 });

  const load = async () => {
    const [l, p] = await Promise.allSettled([fetchLeads(), fetchPipeline()]);
    if (l.status === 'fulfilled') setLeads(l.value);
    if (p.status === 'fulfilled') setPipeline(p.value);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    await createLead(form);
    setForm({ name: '', company: '', email: '', source: '', deal_value: 0 });
    setShowCreate(false);
    load();
  };

  const handleStageChange = async (leadId, newStage) => {
    await updateLead(leadId, { pipeline_stage: newStage });
    load();
  };

  const handleDelete = async (leadId) => {
    await deleteLead(leadId);
    setSelectedLead(null);
    load();
  };

  const filtered = filter === 'all' ? leads : leads.filter((l) => l.pipeline_stage === filter);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={14} className="text-blue-400" />
          <span className="text-xs font-semibold text-gray-300">Revenue CRM</span>
          <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 rounded-full">{leads.length}</span>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-ghost text-xs py-1 px-2">
          <Plus size={12} />
        </button>
      </div>

      {/* Pipeline Summary */}
      {pipeline && (
        <div className="card p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Pipeline</span>
            <span className="text-xs font-bold text-emerald-400">
              <DollarSign size={10} className="inline" />{pipeline.total_pipeline_value?.toLocaleString() || 0}
            </span>
          </div>
          <div className="flex gap-1">
            {STAGES.filter((s) => s !== 'churned').map((stage) => {
              const data = pipeline.stages?.[stage] || { count: 0 };
              return (
                <div key={stage} className="flex-1 text-center">
                  <div className="text-sm font-bold">{data.count}</div>
                  <div className="text-[9px] text-gray-600">{stage.replace('_', ' ')}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Stage Filters */}
      <div className="flex gap-1 flex-wrap">
        <button onClick={() => setFilter('all')}
          className={`text-[10px] px-2 py-0.5 rounded-full ${filter === 'all' ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'}`}>
          all ({leads.length})
        </button>
        {STAGES.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`text-[10px] px-2 py-0.5 rounded-full ${filter === s ? STAGE_COLORS[s] : 'text-gray-500 hover:text-gray-300'}`}>
            {s.replace('_', ' ')} ({leads.filter((l) => l.pipeline_stage === s).length})
          </button>
        ))}
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="card p-3 space-y-2">
          <div className="text-[11px] font-semibold text-gray-400 mb-1">Add Lead</div>
          <div className="grid grid-cols-2 gap-2">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Name *" className="input text-xs" />
            <input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })}
              placeholder="Company" className="input text-xs" />
            <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="Email" className="input text-xs" />
            <input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}
              placeholder="Source (linkedin, referral...)" className="input text-xs" />
          </div>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <DollarSign size={10} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-600" />
              <input type="number" value={form.deal_value} onChange={(e) => setForm({ ...form, deal_value: parseFloat(e.target.value) || 0 })}
                placeholder="Deal value" className="input text-xs pl-6 w-full" />
            </div>
            <button onClick={handleCreate} disabled={!form.name.trim()} className="btn-primary text-xs px-4 disabled:opacity-40">Add Lead</button>
          </div>
        </div>
      )}

      {/* Lead Detail Panel */}
      {selectedLead && (
        <div className="card p-3 space-y-2 border-blue-500/20">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">{selectedLead.name}</div>
              <div className="text-[10px] text-gray-500">{selectedLead.company || 'No company'} {selectedLead.email && `• ${selectedLead.email}`}</div>
            </div>
            <button onClick={() => setSelectedLead(null)} className="text-[10px] text-gray-600 hover:text-gray-300">Close</button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500">Stage:</span>
            <select
              value={selectedLead.pipeline_stage}
              onChange={(e) => { handleStageChange(selectedLead.id, e.target.value); setSelectedLead({ ...selectedLead, pipeline_stage: e.target.value }); }}
              className="input text-xs py-0.5"
            >
              {STAGES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
            </select>
            <span className="text-[10px] text-gray-500 ml-2">Value: ${selectedLead.deal_value?.toLocaleString() || 0}</span>
          </div>
          {selectedLead.notes && <div className="text-[10px] text-gray-500 whitespace-pre-wrap">{selectedLead.notes}</div>}
          <div className="flex gap-1">
            <button onClick={() => handleDelete(selectedLead.id)} className="text-[10px] text-red-400 hover:text-red-300">Delete</button>
          </div>
        </div>
      )}

      {/* Lead List */}
      <div className="space-y-1">
        {filtered.map((lead) => (
          <div key={lead.id} onClick={() => setSelectedLead(lead)}
            className="card-hover p-2.5 flex items-center justify-between cursor-pointer animate-slide-up">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium">{lead.name}</span>
                <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${STAGE_COLORS[lead.pipeline_stage] || ''}`}>
                  {lead.pipeline_stage?.replace('_', ' ')}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-gray-600">
                {lead.company && <span>{lead.company}</span>}
                {lead.source && <span>via {lead.source}</span>}
                {lead.next_followup && <span>Follow up: {lead.next_followup}</span>}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {lead.deal_value > 0 && <span className="text-[10px] text-emerald-400">${lead.deal_value.toLocaleString()}</span>}
              <ChevronRight size={12} className="text-gray-700" />
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-[11px] text-gray-700 text-center py-6">No leads yet. Add your first one!</div>
        )}
      </div>
    </div>
  );
}
