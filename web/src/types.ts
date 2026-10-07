export type DriftStatus = 'LIVE' | 'STALE' | 'UNKNOWN';
export type AlertSeverity = 'high' | 'medium' | 'low';
export type AlertKind = 'drift' | 'stale-pr' | 'dependabot' | 'actions-failure';

export interface CommitInfo {
  sha: string;
  fullSha: string;
  message: string;
  committedAt: string;
  author: string;
}

export interface ActionsRun {
  name: string;
  conclusion: string;
  startedAt: string;
  url: string;
}

export interface StalePR {
  number: number;
  title: string;
  updatedAt: string;
  daysStale: number;
  url: string;
  author: string;
}

export interface PRInfo {
  open: number;
  stale: StalePR[];
}

export interface DependabotInfo {
  total: number;
  bySeverity: { critical: number; high: number; moderate: number; low: number };
}

export interface StampInfo {
  deployedAt: string;
  source: string;
  sourceLabel: string;
  sha: string | null;
  reportedAt: string;
  note: string;
}

export interface DriftInfo {
  status: DriftStatus;
  gapText: string;
  evidence: string;
}

export interface RepoEntry {
  repo: string;
  githubUrl: string;
  liveUrl: string;
  targetKind: string;
  targetLabel: string;
  drift: DriftInfo;
  latestCommit: CommitInfo;
  commitHistory: CommitInfo[];
  actions: ActionsRun | null;
  actionsHistory: ActionsRun[];
  prs: PRInfo;
  dependabot: DependabotInfo;
  githubDeployments: number;
  stamp: StampInfo | null;
}

export interface FleetData {
  computedAt: string;
  repos: RepoEntry[];
}

export interface DriftEntry {
  repo: string;
  liveUrl: string;
  githubUrl: string;
  status: DriftStatus;
  gapText: string;
  evidence: string;
  committedAt: string;
  deployedAt: string | null;
  message: string;
}

export interface DriftData {
  computedAt: string;
  stale: DriftEntry[];
  live: DriftEntry[];
  unknown: DriftEntry[];
}

export interface AlertItem {
  severity: AlertSeverity;
  kind: AlertKind;
  repo: string;
  title: string;
  detail: string;
  url: string;
}

export interface AlertsData {
  computedAt: string;
  alerts: AlertItem[];
}

export interface StampData {
  repo: string;
  sha: string;
  builtAt: string;
  target: string;
}
