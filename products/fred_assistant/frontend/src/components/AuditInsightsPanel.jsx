import { useState } from 'react';
import {
  Shield, ShieldAlert, AlertTriangle, Info, ChevronDown, ChevronRight,
  Wrench, MessageSquare, CheckCircle2, XCircle, FileCode, Bug, Zap, Eye,
} from 'lucide-react';
import { applyAuditFix } from '../api';
import AuditChatPanel from './AuditChatPanel';

const SEVERITY_CONFIG = {
  critical: { bg: 'bg-red-600/20', text: 'text-red-400', icon: ShieldAlert, label: 'Critical' },
  high:     { bg: 'bg-red-500/20', text: 'text-red-400', icon: AlertTriangle, label: 'High' },
  medium:   { bg: 'bg-amber-500/20', text: 'text-amber-400', icon: AlertTriangle, label: 'Medium' },
  low:      { bg: 'bg-gray-500/20', text: 'text-gray-400', icon: Info, label: 'Low' },
  info:     { bg: 'bg-blue-500/20', text: 'text-blue-400', icon: Info, label: 'Info' },
};

const CATEGORY_ICON = {
  security: Shield, performance: Zap, quality: Eye, bug: Bug, style: FileCode, 'best-practice': CheckCircle2,
};

function SeverityBadge({ severity }) {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
}

function FindingCard({ finding, projectName, onDiscuss }) {
  const [expanded, setExpanded] = useState(false);
  const [fixState, setFixState] = useState(null); // null | 'applying' | 'applied' | 'failed'

  const severityCfg = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.info;
  const CategoryIcon = CATEGORY_ICON[finding.category] || FileCode;

  const handleApplyFix = async (e) => {
    e.stopPropagation();
    if (!finding.suggested_fix || !finding.file) return;
    setFixState('applying');
    try {
      const result = await applyAuditFix(
        projectName, finding.file, finding.id,
        finding.code_snippet || '', finding.suggested_fix, finding.description || '',
      );
      setFixState(result.success ? 'applied' : 'failed');
    } catch {
      setFixState('failed');
    }
  };

  return (
    <div className="rounded bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors">
      {/* Header — always visible */}
      <div className="flex items-center gap-2 p-2 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        {expanded ? <ChevronDown size={10} className="text-gray-500 flex-shrink-0" />
                   : <ChevronRight size={10} className="text-gray-500 flex-shrink-0" />}
        <SeverityBadge severity={finding.severity} />
        <CategoryIcon size={10} className={severityCfg.text} />
        <span className="text-[11px] text-gray-300 font-medium flex-1 truncate">{finding.title}</span>
        {finding.file && (
          <span className="text-[9px] text-gray-600 font-mono flex-shrink-0 max-w-[120px] truncate" title={`${finding.file}:${finding.line}`}>
            {finding.file}{finding.line ? `:${finding.line}` : ''}
          </span>
        )}
        {fixState === 'applied' && <CheckCircle2 size={10} className="text-emerald-400 flex-shrink-0" />}
        {fixState === 'failed' && <XCircle size={10} className="text-red-400 flex-shrink-0" />}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-2 pb-2 space-y-2 border-t border-white/5">
          {/* Description */}
          <p className="text-[10px] text-gray-400 leading-relaxed mt-2">{finding.description}</p>

          {/* Code snippet (problem) */}
          {finding.code_snippet && (
            <div>
              <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-0.5">Current Code</div>
              <pre className="text-[10px] text-red-300/80 bg-red-500/5 border border-red-500/10 rounded p-1.5 font-mono whitespace-pre-wrap overflow-x-auto max-h-32">
                {finding.code_snippet}
              </pre>
            </div>
          )}

          {/* Suggested fix */}
          {finding.suggested_fix && (
            <div>
              <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-0.5">Suggested Fix</div>
              <pre className="text-[10px] text-emerald-300/80 bg-emerald-500/5 border border-emerald-500/10 rounded p-1.5 font-mono whitespace-pre-wrap overflow-x-auto max-h-32">
                {finding.suggested_fix}
              </pre>
            </div>
          )}

          {/* Explanation */}
          {finding.explanation && (
            <p className="text-[10px] text-gray-500 italic">{finding.explanation}</p>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-1.5 pt-1">
            {finding.suggested_fix && finding.file && fixState !== 'applied' && (
              <button onClick={handleApplyFix} disabled={fixState === 'applying'}
                className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 flex items-center gap-1 transition-colors">
                <Wrench size={8} />
                {fixState === 'applying' ? 'Applying...' : 'Apply Fix'}
              </button>
            )}
            {fixState === 'applied' && (
              <span className="text-[9px] text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={8} /> Applied
              </span>
            )}
            {fixState === 'failed' && (
              <span className="text-[9px] text-red-400 flex items-center gap-1">
                <XCircle size={8} /> Failed
              </span>
            )}
            <button onClick={(e) => { e.stopPropagation(); onDiscuss(finding); }}
              className="text-[9px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 flex items-center gap-1 transition-colors">
              <MessageSquare size={8} /> Discuss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AuditInsightsPanel({ findings, result, projectName, onClose }) {
  const [showChat, setShowChat] = useState(false);
  const [focusedFinding, setFocusedFinding] = useState(null);

  const severityCounts = findings.reduce((acc, f) => {
    acc[f.severity] = (acc[f.severity] || 0) + 1;
    return acc;
  }, {});

  const handleDiscuss = (finding) => {
    setFocusedFinding(finding);
    setShowChat(true);
  };

  return (
    <div className="mt-2 p-2 rounded bg-white/[0.02] border border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h5 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1">
          <Shield size={10} /> Audit Insights
        </h5>
        <button onClick={onClose} className="text-[9px] text-gray-600 hover:text-gray-400">dismiss</button>
      </div>

      {/* Severity summary + meta */}
      <div className="flex items-center gap-1.5 flex-wrap mb-2">
        {['critical', 'high', 'medium', 'low', 'info'].map((sev) =>
          severityCounts[sev] ? (
            <span key={sev} className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${SEVERITY_CONFIG[sev].bg} ${SEVERITY_CONFIG[sev].text}`}>
              {SEVERITY_CONFIG[sev].label}: {severityCounts[sev]}
            </span>
          ) : null
        )}
        {result?.agents_used?.length > 0 && (
          <span className="text-[9px] text-gray-600 ml-auto">
            {result.agents_used.join(', ')} | {result.total_time?.toFixed(1)}s
          </span>
        )}
      </div>

      {/* Finding cards */}
      <div className="space-y-1 max-h-80 overflow-y-auto">
        {findings.map((f) => (
          <FindingCard key={f.id} finding={f} projectName={projectName} onDiscuss={handleDiscuss} />
        ))}
      </div>

      {/* Chat toggle */}
      {!showChat && (
        <button onClick={() => { setFocusedFinding(null); setShowChat(true); }}
          className="mt-2 w-full text-[9px] py-1 rounded-full bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 flex items-center justify-center gap-1 transition-colors">
          <MessageSquare size={9} /> Ask about these findings
        </button>
      )}

      {/* Chat panel */}
      {showChat && (
        <AuditChatPanel
          projectName={projectName}
          findings={findings}
          focusedFinding={focusedFinding}
          onClose={() => { setShowChat(false); setFocusedFinding(null); }}
        />
      )}
    </div>
  );
}
