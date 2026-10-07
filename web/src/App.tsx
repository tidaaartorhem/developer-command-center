import { useEffect, useMemo, useState } from 'react';
import type {
  AlertItem,
  AlertsData,
  DriftData,
  DriftEntry,
  FleetData,
  RepoEntry,
  StampData,
} from './types';
import {
  actionsClass,
  driftBadge,
  formatDateTime,
  shortSha,
  timeAgo,
} from './lib/format';

type Tab = 'fleet' | 'drift' | 'alerts';

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${path}?v=${Date.now()}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`failed to load ${path}: ${res.status}`);
  return (await res.json()) as T;
}

function ExternalLinks({ repo }: { repo: Pick<RepoEntry, 'liveUrl' | 'githubUrl'> }) {
  return (
    <div className="card-links">
      <a href={repo.liveUrl} target="_blank" rel="noreferrer">Live site ↗</a>
      <a href={repo.githubUrl} target="_blank" rel="noreferrer">GitHub ↗</a>
    </div>
  );
}

function ActionsBadge({ entry }: { entry: RepoEntry }) {
  if (!entry.actions) return <span className="badge badge-unknown">NO CI</span>;
  const { conclusion, name, url } = entry.actions;
  return (
    <a href={url} target="_blank" rel="noreferrer" title={`${name}: ${conclusion}`}>
      <span className={actionsClass(conclusion)}>{conclusion.toUpperCase()}</span>
    </a>
  );
}

function DepChips({ entry }: { entry: RepoEntry }) {
  const staleCount = entry.prs.stale.length;
  const dep = entry.dependabot;
  const sev = dep.bySeverity;
  const sevText = [`critical ${sev.critical}`, `high ${sev.high}`, `moderate ${sev.moderate}`, `low ${sev.low}`].join(' · ');
  return (
    <>
      <span className={staleCount > 0 ? 'chip warn' : 'chip'} title="stale pull requests">
        {staleCount} stale PR{staleCount === 1 ? '' : 's'}
      </span>
      <span className={dep.total > 0 ? 'chip warn' : 'chip ok'} title={`Dependabot: ${sevText}`}>
        {dep.total} Dependabot
      </span>
      {dep.total > 0 && <span className="sev faint">{sevText}</span>}
    </>
  );
}

function RepoCard({ entry, onOpen }: { entry: RepoEntry; onOpen: (repo: string) => void }) {
  const badge = driftBadge(entry.drift.status);
  const lc = entry.latestCommit;
  return (
    <div className="card clickable" onClick={() => onOpen(entry.repo)} role="button" tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onOpen(entry.repo); }}>
      <div className="card-head">
        <h3><button onClick={(e) => { e.stopPropagation(); onOpen(entry.repo); }}>{entry.repo}</button></h3>
        <span className={`${badge.className} badge-big`}>{badge.label}</span>
      </div>
      <div className="meta-line">
        <span>{entry.targetLabel}</span>
        <ActionsBadge entry={entry} />
      </div>
      <div className="commit-line">
        <span className="mono">{shortSha(lc.sha)}</span>{' '}
        <span className="msg">{lc.message}</span>{' '}
        <span className="when">· {timeAgo(lc.committedAt)}</span>
      </div>
      <div className="meta-line">
        <DepChips entry={entry} />
      </div>
      <div onClick={(e) => e.stopPropagation()}><ExternalLinks repo={entry} /></div>
    </div>
  );
}

function DriftRow({ entry, onOpen }: { entry: DriftEntry; onOpen: (repo: string) => void }) {
  const badge = driftBadge(entry.status);
  return (
    <div className="drift-row" onClick={() => onOpen(entry.repo)} role="button" tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onOpen(entry.repo); }}>
      <div className="drift-row-top">
        <h3>{entry.repo}</h3>
        <span className={`${badge.className} badge-big`}>{badge.label}</span>
      </div>
      <div className="meta-line" style={{ marginTop: 8 }}>
        <span className="gap-math">{entry.gapText}</span>
        <span className="faint">· latest push {timeAgo(entry.committedAt)}</span>
        {entry.deployedAt && <span className="faint">· last deploy {timeAgo(entry.deployedAt)}</span>}
      </div>
      <div className="evidence">{entry.evidence}</div>
      <div className="meta-line" style={{ marginTop: 10 }}>
        <a href={entry.liveUrl} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>Live site ↗</a>
        <a href={entry.githubUrl} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>GitHub ↗</a>
      </div>
    </div>
  );
}

function RepoDetail({ entry, onBack }: { entry: RepoEntry; onBack: () => void }) {
  const badge = driftBadge(entry.drift.status);
  const sev = entry.dependabot.bySeverity;
  return (
    <div>
      <div className="detail-head">
        <button className="back-btn" onClick={onBack}>← Fleet</button>
        <h2>{entry.repo}</h2>
        <span className={`${badge.className} badge-big`}>{badge.label}</span>
        <span className="dim">{entry.targetLabel}</span>
      </div>
      <div className="sections">
        <div className="section">
          <h3>Commits</h3>
          {entry.commitHistory.length === 0 && <div className="empty">No commit history recorded.</div>}
          {entry.commitHistory.map((c) => (
            <div className="row" key={c.sha}>
              <span className="mono" title={c.fullSha}>{shortSha(c.sha)}</span>{' '}
              <span className="title">{c.message}</span>
              <div className="faint">{c.author} · {formatDateTime(c.committedAt)} ({timeAgo(c.committedAt)})</div>
            </div>
          ))}
        </div>
        <div className="section">
          <h3>GitHub Actions</h3>
          {entry.actionsHistory.length === 0 && <div className="empty">No Actions runs recorded.</div>}
          {entry.actionsHistory.map((r, i) => (
            <div className="row" key={i}>
              <a href={r.url} target="_blank" rel="noreferrer" className="title">{r.name}</a>{' '}
              <span className={actionsClass(r.conclusion)}>{r.conclusion.toUpperCase()}</span>
              <div className="faint">{formatDateTime(r.startedAt)} ({timeAgo(r.startedAt)})</div>
            </div>
          ))}
        </div>
        <div className="section">
          <h3>Stale PRs <span className="chip">{entry.prs.stale.length}</span></h3>
          <div className="faint" style={{ marginBottom: 6 }}>{entry.prs.open} open total · stale after 14 days untouched</div>
          {entry.prs.stale.length === 0 && <div className="empty">No stale PRs.</div>}
          {entry.prs.stale.map((p) => (
            <div className="row" key={p.number}>
              <a href={p.url} target="_blank" rel="noreferrer" className="title">#{p.number} {p.title}</a>
              <div className="faint">{p.author} · untouched {p.daysStale}d ({formatDateTime(p.updatedAt)})</div>
            </div>
          ))}
        </div>
        <div className="section">
          <h3>Dependabot <span className="chip">{entry.dependabot.total}</span></h3>
          {entry.dependabot.total === 0 && <div className="empty">No open Dependabot alerts.</div>}
          {entry.dependabot.total > 0 && (
            <div className="row">
              <span className="sev">
                critical {sev.critical} · high {sev.high} · moderate {sev.moderate} · low {sev.low}
              </span>
            </div>
          )}
        </div>
        <div className="section full">
          <h3>Live stamp</h3>
          {entry.stamp ? (
            <div className="stamp-box">
              <div><strong>Deployed:</strong> <span className="mono">{formatDateTime(entry.stamp.deployedAt)}</span> ({timeAgo(entry.stamp.deployedAt)})</div>
              <div><strong>Source:</strong> {entry.stamp.sourceLabel}</div>
              {entry.stamp.sha && <div><strong>SHA:</strong> <span className="mono">{shortSha(entry.stamp.sha)}</span></div>}
              <div className="faint">{entry.stamp.note}</div>
            </div>
          ) : (
            <div className="stamp-missing">
              No live stamp recorded yet — deploy, then run <span className="mono">python3 services/report_stamp.py</span>.
            </div>
          )}
          <div className="note">
            GitHub deployments recorded: <strong className="mono">{entry.githubDeployments}</strong>. GitHub records
            no deployments for this fleet — that gap is why stamps exist.
          </div>
        </div>
      </div>
    </div>
  );
}

function AlertRow({ alert }: { alert: AlertItem }) {
  return (
    <div className={`alert-row ${alert.severity}`}>
      <span className="sev-label">{alert.severity}</span>
      <div className="body">
        <div className="title"><a href={alert.url} target="_blank" rel="noreferrer">{alert.title}</a></div>
        <div className="detail">{alert.detail}</div>
        <div className="faint" style={{ marginTop: 4 }}>{alert.repo} · {alert.kind}</div>
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>('fleet');
  const [fleet, setFleet] = useState<FleetData | null>(null);
  const [drift, setDrift] = useState<DriftData | null>(null);
  const [alerts, setAlerts] = useState<AlertsData | null>(null);
  const [stamp, setStamp] = useState<StampData | null>(null);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchJson<FleetData>('./fleet.json'),
      fetchJson<DriftData>('./drift.json'),
      fetchJson<AlertsData>('./alerts.json'),
      fetchJson<StampData>('./stamp.json'),
    ])
      .then(([f, d, a, s]) => {
        setFleet(f); setDrift(d); setAlerts(a); setStamp(s);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const detailEntry = useMemo(
    () => fleet?.repos.find((r) => r.repo === selectedRepo) ?? null,
    [fleet, selectedRepo],
  );

  if (error) {
    return (
      <div className="app">
        <div className="error">
          <div className="card">
            <h3>Couldn&apos;t load fleet data</h3>
            <p className="dim">{error}</p>
            <p className="faint">The data JSONs are generated by the pipeline before build. Re-run the build and check the console output.</p>
          </div>
        </div>
      </div>
    );
  }
  if (!fleet || !drift || !alerts) {
    return <div className="app"><div className="loading">Loading fleet…</div></div>;
  }

  const live = fleet.repos.filter((r) => r.drift.status === 'LIVE').length;
  const stale = fleet.repos.filter((r) => r.drift.status === 'STALE').length;
  const unknown = fleet.repos.filter((r) => r.drift.status === 'UNKNOWN').length;
  const highAlerts = alerts.alerts.filter((a) => a.severity === 'high').length;

  if (detailEntry) {
    return (
      <div className="app">
        <RepoDetail entry={detailEntry} onBack={() => setSelectedRepo(null)} />
      </div>
    );
  }

  return (
    <div className="app">
      <div className="topbar">
        <div>
          <h1>Developer <span className="accent">Command Center</span></h1>
          <div className="subhead">Fleet health across {fleet.repos.length} shipped repos.</div>
          <div className="computed mono">computed {formatDateTime(fleet.computedAt)}</div>
        </div>
        <div className="summary-row">
          <span className="summary-pill live"><span className="n">{live}</span> live</span>
          <span className="summary-pill stale"><span className="n">{stale}</span> stale</span>
          <span className="summary-pill unknown"><span className="n">{unknown}</span> unknown</span>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab${tab === 'fleet' ? ' active' : ''}`} onClick={() => setTab('fleet')}>
          Fleet overview
        </button>
        <button className={`tab${tab === 'drift' ? ' active' : ''}`} onClick={() => setTab('drift')}>
          Drift board<span className="count alert">{stale}</span>
        </button>
        <button className={`tab${tab === 'alerts' ? ' active' : ''}`} onClick={() => setTab('alerts')}>
          Alerts<span className={highAlerts > 0 ? 'count alert' : 'count'}>{alerts.alerts.length}</span>
        </button>
      </div>

      {tab === 'fleet' && (
        <div className="grid">
          {fleet.repos.map((r) => (
            <RepoCard key={r.repo} entry={r} onOpen={setSelectedRepo} />
          ))}
        </div>
      )}

      {tab === 'drift' && (
        <div>
          <div className="explainer">
            <strong>Drift</strong> = the latest push on main is newer than the last known live stamp.
            GitHub records no deployments for this fleet, so each repo&apos;s deploy target (Firebase Hosting
            release or App Hosting rollout) is stamped separately after deploy — drift is computed
            push-vs-stamp, not from GitHub.
          </div>
          {drift.stale.length > 0 && (
            <>
              <div className="drift-group-label">Stale — needs a deploy</div>
              <div className="drift-list">
                {drift.stale.map((e) => <DriftRow key={e.repo} entry={e} onOpen={setSelectedRepo} />)}
              </div>
            </>
          )}
          <div className="drift-group-label">Live</div>
          <div className="drift-list">
            {drift.live.length === 0 && <div className="empty">None live right now.</div>}
            {drift.live.map((e) => <DriftRow key={e.repo} entry={e} onOpen={setSelectedRepo} />)}
          </div>
          <div className="drift-group-label">Unknown</div>
          <div className="drift-list">
            {drift.unknown.length === 0 && <div className="empty">None unknown.</div>}
            {drift.unknown.map((e) => <DriftRow key={e.repo} entry={e} onOpen={setSelectedRepo} />)}
          </div>
        </div>
      )}

      {tab === 'alerts' && (
        <div className="alert-list">
          {alerts.alerts.length === 0 && <div className="empty">No alerts. Fleet is quiet.</div>}
          {alerts.alerts.map((a) => <AlertRow key={`${a.kind}-${a.repo}-${a.title}`} alert={a} />)}
        </div>
      )}

      {stamp && (
        <div className="faint mono" style={{ marginTop: 28, fontSize: '0.75rem' }}>
          this console · {stamp.repo}@{shortSha(stamp.sha)} · built {formatDateTime(stamp.builtAt)} → {stamp.target}
        </div>
      )}
    </div>
  );
}
