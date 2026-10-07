import type { DriftStatus } from '../types';

/** "2026-10-06T12:59:30Z" -> "17h ago" style relative time. */
export function timeAgo(iso: string, nowIso?: string): string {
  const then = Date.parse(iso);
  const now = nowIso ? Date.parse(nowIso) : Date.now();
  if (Number.isNaN(then) || Number.isNaN(now)) return '—';
  const diffMs = now - then;
  if (diffMs < 0) return 'just now';
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

/** 43 -> "43s", 5400 -> "1h 30m", 90061 -> "1d 1h". Largest two units, capped. */
export function formatGap(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const parts: string[] = [];
  const d = Math.floor(s / 86_400);
  const h = Math.floor((s % 86_400) / 3_600);
  const m = Math.floor((s % 3_600) / 60);
  const sec = s % 60;
  if (d > 0) parts.push(`${d}d`);
  if (h > 0) parts.push(`${h}h`);
  if (m > 0 && d === 0) parts.push(`${m}m`);
  if (sec > 0 && h === 0 && d === 0) parts.push(`${sec}s`);
  return parts.length > 0 ? parts.slice(0, 2).join(' ') : '0s';
}

/** First 7 hex chars of a SHA, or the input trimmed when shorter. */
export function shortSha(sha: string | null | undefined): string {
  if (!sha) return '—';
  return sha.trim().slice(0, 7);
}

export interface DriftBadge {
  label: string;
  className: string;
}

/** Maps drift status to a display label + CSS class. */
export function driftBadge(status: DriftStatus): DriftBadge {
  switch (status) {
    case 'LIVE':
      return { label: 'LIVE', className: 'badge badge-live' };
    case 'STALE':
      return { label: 'STALE', className: 'badge badge-stale' };
    case 'UNKNOWN':
      return { label: 'UNKNOWN', className: 'badge badge-unknown' };
  }
}

/** Actions conclusion -> badge CSS class. */
export function actionsClass(conclusion: string | null | undefined): string {
  const c = (conclusion ?? '').toLowerCase();
  if (c === 'success') return 'badge badge-live';
  if (c === 'failure' || c === 'cancelled' || c === 'timed_out') return 'badge badge-stale';
  return 'badge badge-unknown';
}

/** UTC "Oct 6, 2026, 12:59" for stamps and commit times. */
export function formatDateTime(iso: string): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '—';
  return new Date(t).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  }) + ' UTC';
}
