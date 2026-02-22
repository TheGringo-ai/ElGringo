export const API_URL = import.meta.env.VITE_API_URL || '/api';

export const PRIORITY_COLORS = {
  1: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', label: 'P1' },
  2: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30', label: 'P2' },
  3: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30', label: 'P3' },
  4: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30', label: 'P4' },
  5: { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30', label: 'P5' },
};

export const STATUS_COLUMNS = {
  backlog: { label: 'Backlog', statuses: ['backlog', 'sprint'] },
  in_progress: { label: 'In Progress', statuses: ['in_progress'] },
  review: { label: 'Review', statuses: ['review'] },
  done: { label: 'Done', statuses: ['done'] },
};

export const CONTENT_TYPES = [
  { value: 'linkedin_post', label: 'LinkedIn Post' },
  { value: 'blog_post', label: 'Blog Post' },
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'release_notes', label: 'Release Notes' },
];

export const METRIC_COLORS = {
  sprint: 'text-blue-400',
  active: 'text-amber-400',
  content: 'text-purple-400',
  scheduler: 'text-emerald-400',
  days: 'text-red-400',
};
