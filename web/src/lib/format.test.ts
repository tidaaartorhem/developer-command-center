import { describe, expect, it } from 'vitest';
import { actionsClass, driftBadge, formatDateTime, formatGap, shortSha, timeAgo } from './format';

const NOW = '2026-10-07T12:00:00Z';

describe('timeAgo', () => {
  it('returns just now for sub-minute differences', () => {
    expect(timeAgo('2026-10-07T11:59:30Z', NOW)).toBe('just now');
  });
  it('formats minutes', () => {
    expect(timeAgo('2026-10-07T11:45:00Z', NOW)).toBe('15m ago');
  });
  it('formats hours', () => {
    expect(timeAgo('2026-10-06T18:00:00Z', NOW)).toBe('18h ago');
  });
  it('formats days', () => {
    expect(timeAgo('2026-09-10T00:00:00Z', NOW)).toBe('27d ago');
  });
  it('formats months', () => {
    expect(timeAgo('2026-04-01T00:00:00Z', NOW)).toBe('6mo ago');
  });
  it('handles invalid input', () => {
    expect(timeAgo('not-a-date', NOW)).toBe('—');
  });
});

describe('formatGap', () => {
  it('formats seconds', () => {
    expect(formatGap(43)).toBe('43s');
  });
  it('formats hours and minutes', () => {
    expect(formatGap(5400)).toBe('1h 30m');
  });
  it('formats days and hours', () => {
    expect(formatGap(90_061)).toBe('1d 1h');
  });
  it('formats exact minutes', () => {
    expect(formatGap(120)).toBe('2m');
  });
  it('handles zero', () => {
    expect(formatGap(0)).toBe('0s');
  });
  it('drops seconds when hours are present', () => {
    expect(formatGap(3723)).toBe('1h 2m');
  });
});

describe('driftBadge', () => {
  it('maps LIVE', () => {
    expect(driftBadge('LIVE')).toEqual({ label: 'LIVE', className: 'badge badge-live' });
  });
  it('maps STALE', () => {
    expect(driftBadge('STALE')).toEqual({ label: 'STALE', className: 'badge badge-stale' });
  });
  it('maps UNKNOWN', () => {
    expect(driftBadge('UNKNOWN')).toEqual({ label: 'UNKNOWN', className: 'badge badge-unknown' });
  });
});

describe('shortSha', () => {
  it('truncates long SHAs to 7 chars', () => {
    expect(shortSha('a6f0840abcdef123456')).toBe('a6f0840');
  });
  it('handles short input', () => {
    expect(shortSha('abc')).toBe('abc');
  });
  it('handles null and undefined', () => {
    expect(shortSha(null)).toBe('—');
    expect(shortSha(undefined)).toBe('—');
  });
});

describe('actionsClass', () => {
  it('success maps to live style', () => {
    expect(actionsClass('success')).toBe('badge badge-live');
  });
  it('failure maps to stale style', () => {
    expect(actionsClass('failure')).toBe('badge badge-stale');
  });
  it('in_progress maps to unknown style', () => {
    expect(actionsClass('in_progress')).toBe('badge badge-unknown');
  });
  it('null maps to unknown style', () => {
    expect(actionsClass(null)).toBe('badge badge-unknown');
  });
});

describe('formatDateTime', () => {
  it('formats an ISO timestamp in UTC', () => {
    expect(formatDateTime('2026-10-06T12:59:30Z')).toBe('Oct 6, 2026, 12:59 UTC');
  });
  it('handles invalid input', () => {
    expect(formatDateTime('garbage')).toBe('—');
  });
});
