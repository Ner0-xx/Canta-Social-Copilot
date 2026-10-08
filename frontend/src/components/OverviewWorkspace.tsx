import {
  AlertCircle,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FilePenLine,
  Lightbulb,
  Linkedin,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { getDrafts, getOAuthStatus, getScheduledJobs } from "../lib/api";
import type { ContentDraftData, OAuthConnectionData, ScheduledJob } from "../types";

type PlatformStatus = {
  data: OAuthConnectionData | null;
  error: boolean;
};

function formatSchedule(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Time unavailable"
    : new Intl.DateTimeFormat(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(date);
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function OverviewWorkspace({
  onNavigate,
}: {
  onNavigate: (tab: "content" | "ideas" | "sources" | "calendar" | "analytics" | "settings") => void;
}) {
  const [drafts, setDrafts] = useState<ContentDraftData[] | null>(null);
  const [jobs, setJobs] = useState<ScheduledJob[] | null>(null);
  const [linkedin, setLinkedin] = useState<PlatformStatus>({ data: null, error: false });
  const [x, setX] = useState<PlatformStatus>({ data: null, error: false });
  const [refreshing, setRefreshing] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setLoadError(null);
    const [draftsResult, jobsResult, linkedinResult, xResult] = await Promise.allSettled([
      getDrafts(),
      getScheduledJobs(),
      getOAuthStatus("linkedin"),
      getOAuthStatus("x"),
    ]);

    setDrafts(draftsResult.status === "fulfilled" ? draftsResult.value : null);
    setJobs(jobsResult.status === "fulfilled" ? jobsResult.value : null);
    setLinkedin({
      data: linkedinResult.status === "fulfilled" ? linkedinResult.value : null,
      error: linkedinResult.status === "rejected",
    });
    setX({
      data: xResult.status === "fulfilled" ? xResult.value : null,
      error: xResult.status === "rejected",
    });

    const failures = [draftsResult, jobsResult, linkedinResult, xResult].filter(
      (result) => result.status === "rejected",
    );
    if (failures.length > 0) {
      setLoadError(
        failures.length === 4
          ? "We couldn’t load your workspace overview. Check your connection and try again."
          : "Some overview details couldn’t be loaded. Check the affected sections or try refreshing.",
      );
    }
    setLastUpdated(new Date());
    setHasLoaded(true);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const pendingReview = drafts?.filter((draft) => draft.status === "in_review") ?? [];
  const approved = drafts?.filter((draft) => draft.status === "approved") ?? [];
  const published = drafts?.filter((draft) => draft.status === "published") ?? [];
  const attentionDrafts =
    drafts?.filter(
      (draft) =>
        draft.status !== "published" &&
        draft.status !== "rejected" &&
        (draft.warnings?.length ?? 0) > 0,
    ) ?? [];
  const upcomingJobs = (jobs ?? [])
    .filter((job) => job.status === "pending")
    .sort((left, right) => new Date(left.scheduled_at).getTime() - new Date(right.scheduled_at).getTime());
  const nextJobs = upcomingJobs.slice(0, 3);
  const loading = !hasLoaded;

  return (
    <div className="overview-workspace">
      <section className="overview-hero">
        <div className="overview-hero-copy">
          <span className="overview-eyebrow"><Sparkles size={14} /> YOUR SOCIAL STUDIO</span>
          <h1>{greeting()},<br />let’s make <em>something matter.</em></h1>
          <p>Your ideas, publishing rhythm, and social accounts—together in one calm place.</p>
          <div className="overview-hero-actions">
            <button type="button" className="overview-primary-action" onClick={() => onNavigate("content")}>
              <Plus size={17} /> Create a post
            </button>
            <button type="button" className="overview-secondary-action" onClick={() => onNavigate("ideas")}>
              <Lightbulb size={16} /> Explore ideas <ArrowUpRight size={15} />
            </button>
          </div>
        </div>
        <div className="overview-hero-art" aria-hidden="true">
          <span className="overview-orbit orbit-one" />
          <span className="overview-orbit orbit-two" />
          <span className="overview-orbit orbit-three" />
          <span className="overview-orbit-star star-one">✦</span>
          <span className="overview-orbit-star star-two">✧</span>
          <span className="overview-orbit-core"><Sparkles size={29} /></span>
        </div>
        <div className="overview-date">
          <span>YOUR WORKSPACE</span>
          <strong>{new Intl.DateTimeFormat(undefined, { weekday: "long" }).format(new Date())}</strong>
          <span>{new Intl.DateTimeFormat(undefined, { month: "long", day: "numeric", year: "numeric" }).format(new Date())}</span>
        </div>
      </section>

      {loadError && (
        <div className="overview-error" role="alert">
          <AlertCircle size={18} />
          <span>{loadError}</span>
          <button type="button" onClick={() => void refresh()} disabled={refreshing}>
            <RefreshCw size={14} className={refreshing ? "is-spinning" : undefined} />
            Try again
          </button>
        </div>
      )}

      <div className="overview-section-heading">
        <div>
          <span className="overview-section-kicker">A CLEAR VIEW</span>
          <h2>Your workspace at a glance</h2>
        </div>
        <button type="button" className="overview-refresh" onClick={() => void refresh()} disabled={refreshing}>
          <RefreshCw size={15} className={refreshing ? "is-spinning" : undefined} />
          {refreshing ? "Refreshing" : "Refresh"}
        </button>
      </div>

      <section className="overview-metrics" aria-label="Content pipeline">
        <button type="button" className="overview-metric-card review" onClick={() => onNavigate("content")}>
          <span className="overview-metric-icon"><FilePenLine size={18} /></span>
          <span className="overview-metric-value">{loading ? "—" : drafts === null ? "!" : pendingReview.length}</span>
          <span className="overview-metric-label">Needs your review</span>
          <span className="overview-metric-foot">{drafts === null ? "Draft data unavailable" : "In the approval queue"} <ArrowRight size={13} /></span>
        </button>
        <button type="button" className="overview-metric-card approved" onClick={() => onNavigate("content")}>
          <span className="overview-metric-icon"><CheckCircle2 size={18} /></span>
          <span className="overview-metric-value">{loading ? "—" : drafts === null ? "!" : approved.length}</span>
          <span className="overview-metric-label">Ready to publish</span>
          <span className="overview-metric-foot">{drafts === null ? "Draft data unavailable" : "Approved and awaiting action"} <ArrowRight size={13} /></span>
        </button>
        <button type="button" className="overview-metric-card queued" onClick={() => onNavigate("calendar")}>
          <span className="overview-metric-icon"><CalendarDays size={18} /></span>
          <span className="overview-metric-value">{loading ? "—" : jobs === null ? "!" : upcomingJobs.length}</span>
          <span className="overview-metric-label">Coming up</span>
          <span className="overview-metric-foot">{jobs === null ? "Schedule data unavailable" : "Upcoming scheduled posts"} <ArrowRight size={13} /></span>
        </button>
        <button type="button" className="overview-metric-card published" onClick={() => onNavigate("analytics")}>
          <span className="overview-metric-icon"><Send size={18} /></span>
          <span className="overview-metric-value">{loading ? "—" : drafts === null ? "!" : published.length}</span>
          <span className="overview-metric-label">Published</span>
          <span className="overview-metric-foot">{drafts === null ? "Draft data unavailable" : "Posts in your content history"} <ArrowRight size={13} /></span>
        </button>
      </section>

      <div className="overview-panels">
        <section className="overview-panel overview-accounts">
          <div className="overview-panel-heading">
            <div>
              <span className="overview-section-kicker">READY WHEN YOU ARE</span>
              <h2>Your social accounts</h2>
            </div>
            <button type="button" className="overview-text-link" onClick={() => onNavigate("settings")}>
              Manage <ArrowUpRight size={15} />
            </button>
          </div>
          <div className="overview-account-list">
            <AccountCard name="LinkedIn" platform="linkedin" status={linkedin} onManage={() => onNavigate("settings")} />
            <AccountCard name="X" platform="x" status={x} onManage={() => onNavigate("settings")} />
          </div>
          <div className="overview-note">
            <span className="overview-note-dot" />
            <span>LinkedIn feed and inbox reading aren’t available with current app permissions.</span>
          </div>
        </section>

        <section className="overview-panel overview-upcoming">
          <div className="overview-panel-heading">
            <div>
              <span className="overview-section-kicker">ON THE HORIZON</span>
              <h2>Coming up next</h2>
            </div>
            <button type="button" className="overview-text-link" onClick={() => onNavigate("calendar")}>
              Calendar <ArrowUpRight size={15} />
            </button>
          </div>
          {jobs === null ? (
            <div className="overview-empty"><AlertCircle size={19} /><span>Schedule could not be loaded.</span></div>
          ) : nextJobs.length > 0 ? (
            <div className="overview-schedule-list">
              {nextJobs.map((job) => {
                const draft = drafts?.find((item) => item.id === job.draft_id);
                return (
                  <article className="overview-schedule-item" key={job.id}>
                    <div className={`overview-schedule-platform ${job.platform.toLowerCase()}`}>
                      {job.platform.toLowerCase() === "linkedin" ? <Linkedin size={17} /> : <X size={16} />}
                    </div>
                    <div className="overview-schedule-copy">
                      <strong>{draft?.title || `${job.platform === "x" ? "X" : job.platform} post`}</strong>
                      <span>{draft?.body?.trim().slice(0, 72) || `Draft #${job.draft_id}`}</span>
                    </div>
                    <span className="overview-schedule-time"><Clock3 size={13} />{formatSchedule(job.scheduled_at)}</span>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="overview-empty">
              <div className="overview-empty-icon"><CalendarDays size={20} /></div>
              <strong>A little breathing room.</strong>
              <span>No posts are scheduled yet. Approved content can be queued from your Content workspace.</span>
              <button type="button" onClick={() => onNavigate("content")}>Go to content <ArrowRight size={14} /></button>
            </div>
          )}
          {jobs !== null && nextJobs.length > 0 && (
            <button type="button" className="overview-panel-footer" onClick={() => onNavigate("calendar")}>
              See your full publishing calendar <ArrowRight size={15} />
            </button>
          )}
        </section>
      </div>

      <div className="overview-lower-grid">
        <section className="overview-attention">
          <div className="overview-attention-icon"><AlertCircle size={18} /></div>
          <div className="overview-attention-copy">
            <span className="overview-section-kicker">A QUICK NUDGE</span>
            <h2>{drafts === null ? "Review status unavailable" : attentionDrafts.length > 0 ? `${attentionDrafts.length} draft${attentionDrafts.length === 1 ? "" : "s"} could use a second look` : "You’re all caught up"}</h2>
            <p>
              {drafts === null
                ? "We couldn’t retrieve draft quality warnings. Check the content workspace."
                : attentionDrafts.length > 0
                  ? "Some drafts have quality warnings. Review them before approving or scheduling."
                  : "No unresolved quality warnings are showing in your drafts right now."}
            </p>
          </div>
          <button type="button" onClick={() => onNavigate("content")}>Review drafts <ArrowRight size={15} /></button>
        </section>

        <section className="overview-quick-actions">
          <span className="overview-section-kicker">MAKE YOUR NEXT MOVE</span>
          <div className="overview-quick-action-list">
            <button type="button" onClick={() => onNavigate("ideas")}><span className="ideas"><Lightbulb size={17} /></span><span><strong>Find an idea</strong><small>Turn inspiration into a direction</small></span><ArrowRight size={15} /></button>
            <button type="button" onClick={() => onNavigate("sources")}><span className="sources"><Plus size={17} /></span><span><strong>Add a source</strong><small>Bring useful material into Canta</small></span><ArrowRight size={15} /></button>
          </div>
        </section>
      </div>

      <footer className="overview-updated">
        <span>{lastUpdated ? `Last checked ${lastUpdated.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}` : "Checking workspace"}</span>
        <button type="button" onClick={() => onNavigate("analytics")}>Explore performance <ArrowUpRight size={14} /></button>
      </footer>
    </div>
  );
}

function AccountCard({
  name,
  platform,
  status,
  onManage,
}: {
  name: string;
  platform: "linkedin" | "x";
  status: PlatformStatus;
  onManage: () => void;
}) {
  const connected = status.data?.connected === true;
  const statusLabel = status.error ? "Status unavailable" : connected ? "Connected" : "Not connected";

  return (
    <article className={`overview-account-card ${platform}${connected ? " connected" : ""}`}>
      <div className={`overview-account-logo ${platform}`} aria-hidden="true">
        {platform === "linkedin" ? <Linkedin size={19} /> : <X size={20} />}
      </div>
      <div className="overview-account-copy">
        <div className="overview-account-name">
          <strong>{name}</strong>
          <span className={`overview-connection-pill ${status.error ? "unknown" : connected ? "connected" : "disconnected"}`}>
            {status.error ? <AlertCircle size={12} /> : connected ? <CheckCircle2 size={12} /> : null}
            {statusLabel}
          </span>
        </div>
        {connected ? (
          <>
            <span className="overview-account-handle">{status.data?.account_name || "Account connected"}</span>
            {status.data?.token_expired && <span className="overview-account-warning">Access expired—refresh or reconnect.</span>}
          </>
        ) : status.error ? (
          <span className="overview-account-handle">Couldn’t verify this connection.</span>
        ) : (
          <span className="overview-account-handle">Connect to publish from Canta.</span>
        )}
      </div>
      <button type="button" className="overview-account-manage" onClick={onManage} aria-label={`Manage ${name} connection`}>
        <ArrowUpRight size={16} />
      </button>
    </article>
  );
}
