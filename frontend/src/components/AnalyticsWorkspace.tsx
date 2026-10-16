import {
  ArrowUpRight,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Eye,
  FlaskConical,
  Heart,
  MessageCircle,
  Repeat2,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { getExperiments, request } from "../lib/api";
import type {
  AABExperimentData,
  AnalyticsDashboardData,
  MetricCheckpoint,
  PublishedPublicationData,
  PublishedPublicationsPage,
} from "../types";

function number(value?: number) {
  return (value ?? 0).toLocaleString();
}

function shortDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

type Platform = "x" | "linkedin";
type MetricValues = Record<
  "impressions" | "reactions" | "comments" | "reposts" | "clicks",
  string
>;
const checkpoints: MetricCheckpoint[] = ["24h", "7d", "30d", "90d"];
const checkpointLabels: Record<MetricCheckpoint, string> = {
  "24h": "24 hours",
  "7d": "7 days",
  "30d": "30 days",
  "90d": "90 days",
};

function defaultCheckpoint(publication: PublishedPublicationData): MetricCheckpoint {
  const age = Date.now() - new Date(publication.published_at).getTime();
  if (age >= 90 * 24 * 60 * 60 * 1000) return "90d";
  if (age >= 30 * 24 * 60 * 60 * 1000) return "30d";
  if (age >= 7 * 24 * 60 * 60 * 1000) return "7d";
  return "24h";
}

export function AnalyticsWorkspace() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "experiments">("dashboard");
  const [dashboard, setDashboard] = useState<AnalyticsDashboardData | null>(null);
  const [experiments, setExperiments] = useState<AABExperimentData[]>([]);
  const [recentPosts, setRecentPosts] = useState<Record<Platform, PublishedPublicationData[]>>({
    x: [],
    linkedin: [],
  });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [metricsStatus, setMetricsStatus] = useState<string | null>(null);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<MetricCheckpoint>("7d");
  const [selectedPlatform, setSelectedPlatform] = useState<"all" | Platform>("all");
  const [activeCheckpoints, setActiveCheckpoints] = useState<
    Record<number, MetricCheckpoint>
  >({});
  const [metricDrafts, setMetricDrafts] = useState<Record<string, MetricValues>>({});
  const [savingPublicationId, setSavingPublicationId] = useState<number | null>(null);
  const [archivePlatform, setArchivePlatform] = useState<Platform | null>(null);
  const [archivePage, setArchivePage] = useState<PublishedPublicationsPage | null>(null);
  const [archiveOffset, setArchiveOffset] = useState(0);
  const [archiveSearch, setArchiveSearch] = useState("");
  const [archiveQuery, setArchiveQuery] = useState("");
  const [selectedPublication, setSelectedPublication] =
    useState<PublishedPublicationData | null>(null);

  const fetchDashboard = useCallback(async (
    checkpoint = selectedCheckpoint,
    platform = selectedPlatform,
  ) => {
    setLoadError(null);
    try {
      const [dashboardData, xPosts, linkedinPosts, experimentData] = await Promise.all([
        request<AnalyticsDashboardData>(
          `/api/analytics/dashboard?checkpoint=${checkpoint}&platform=${platform}`,
        ),
        request<PublishedPublicationsPage>("/api/analytics/publications?platform=x&limit=20"),
        request<PublishedPublicationsPage>(
          "/api/analytics/publications?platform=linkedin&limit=20",
        ),
        getExperiments(),
      ]);
      setDashboard(dashboardData);
      setRecentPosts({ x: xPosts.items, linkedin: linkedinPosts.items });
      setExperiments(experimentData);
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Unable to load analytics right now.",
      );
    } finally {
      setLoading(false);
    }
  }, [selectedCheckpoint, selectedPlatform]);

  useEffect(() => {
    void fetchDashboard();
  }, [fetchDashboard]);

  const loadArchive = async (
    platform: Platform,
    offset = archiveOffset,
    search = archiveQuery,
  ) => {
    try {
      const query = new URLSearchParams({
        platform,
        offset: String(offset),
        limit: "50",
        search,
      });
      const page = await request<PublishedPublicationsPage>(
        `/api/analytics/publications?${query.toString()}`,
      );
      setArchivePage(page);
      setArchivePlatform(platform);
      setArchiveOffset(offset);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Could not load published posts.");
    }
  };

  const getMetricValues = (
    publication: PublishedPublicationData,
    checkpoint: MetricCheckpoint,
  ): MetricValues => {
    const key = `${publication.publication_id}:${checkpoint}`;
    const draftValues = metricDrafts[key];
    if (draftValues) return draftValues;
    const saved = publication.metrics[checkpoint];
    return {
      impressions: saved ? String(saved.impressions) : "",
      reactions: saved ? String(saved.reactions) : "",
      comments: saved ? String(saved.comments) : "",
      reposts: saved ? String(saved.reposts) : "",
      clicks: saved ? String(saved.clicks) : "",
    };
  };

  const handleMetricChange = (
    publication: PublishedPublicationData,
    checkpoint: MetricCheckpoint,
    field: keyof MetricValues,
    value: string,
  ) => {
    const key = `${publication.publication_id}:${checkpoint}`;
    setMetricDrafts((current) => ({
      ...current,
      [key]: {
        ...getMetricValues(publication, checkpoint),
        [field]: value.replace(/[^\d]/g, ""),
      },
    }));
  };

  const saveMetrics = async (
    publication: PublishedPublicationData,
    requestedCheckpoint: MetricCheckpoint,
  ) => {
    const age = Date.now() - new Date(publication.published_at).getTime();
    const checkpoint =
      age > 90 * 24 * 60 * 60 * 1000 ? "90d" : requestedCheckpoint;
    const values = getMetricValues(publication, checkpoint);
    setSavingPublicationId(publication.publication_id);
    setMetricsStatus(null);
    try {
      const snapshot = await request<PublishedPublicationData["metrics"][MetricCheckpoint]>(
        `/api/analytics/publications/${publication.publication_id}/metrics`,
        {
          method: "PUT",
          body: JSON.stringify({
            checkpoint,
            impressions: Number(values.impressions) || 0,
            reactions: Number(values.reactions) || 0,
            comments: Number(values.comments) || 0,
            reposts: Number(values.reposts) || 0,
            clicks: Number(values.clicks) || 0,
          }),
        },
      );
      if (!snapshot) throw new Error("Canta returned no saved metrics.");
      const updatePost = (post: PublishedPublicationData) =>
        post.publication_id === publication.publication_id
          ? { ...post, metrics: { ...post.metrics, [snapshot.checkpoint]: snapshot } }
          : post;
      setRecentPosts((current) => ({
        x: current.x.map(updatePost),
        linkedin: current.linkedin.map(updatePost),
      }));
      setArchivePage((current) =>
        current
          ? { ...current, items: current.items.map(updatePost) }
          : current,
      );
      setSelectedPublication((current) => (current ? updatePost(current) : current));
      setMetricDrafts((current) => {
        const next = { ...current };
        delete next[`${publication.publication_id}:${snapshot.checkpoint}`];
        return next;
      });
      setMetricsStatus(
        `${checkpointLabels[snapshot.checkpoint]} metrics saved${
          snapshot.is_late ? " (late entry; marked for careful comparison)" : ""
        }.`,
      );
      await fetchDashboard();
    } catch (error) {
      setMetricsStatus(error instanceof Error ? error.message : "Failed to save metrics.");
    } finally {
      setSavingPublicationId(null);
    }
  };

  const renderMetricEditor = (publication: PublishedPublicationData) => {
    const isOlderThanWindow =
      Date.now() - new Date(publication.published_at).getTime() >
      90 * 24 * 60 * 60 * 1000;
    const checkpoint = isOlderThanWindow
      ? "90d"
      : activeCheckpoints[publication.publication_id] ?? defaultCheckpoint(publication);
    const saved = publication.metrics[checkpoint];
    const values = getMetricValues(publication, checkpoint);

    return (
      <div className="checkpoint-editor">
        <label>
          Measurement checkpoint
          <select
            value={isOlderThanWindow ? "90d" : checkpoint}
            disabled={isOlderThanWindow}
            onChange={(event) =>
              setActiveCheckpoints((current) => ({
                ...current,
                [publication.publication_id]: event.target.value as MetricCheckpoint,
              }))
            }
          >
            {checkpoints.map((item) => (
              <option key={item} value={item}>
                {checkpointLabels[item]}
              </option>
            ))}
          </select>
        </label>
        {isOlderThanWindow && (
          <p className="checkpoint-late-note">
            This post is over 90 days old. Its figures are stored as a late 90-day entry.
          </p>
        )}
        {saved?.is_late && !isOlderThanWindow && (
          <p className="checkpoint-late-note">
            Last updated {shortDate(saved.recorded_at)}; this checkpoint was entered late.
          </p>
        )}
        <div className="metric-input-grid">
          {([
            ["impressions", "Impressions", Eye],
            ["reactions", "Reactions", Heart],
            ["comments", "Comments", MessageCircle],
            ["reposts", "Reposts", Repeat2],
            ["clicks", "Clicks", ArrowUpRight],
          ] as const).map(([field, label, Icon]) => (
            <label className="metric-input" key={field}>
              <span><Icon size={13} />{label}</span>
              <input
                type="number"
                min="0"
                value={values[field]}
                onChange={(event) =>
                  handleMetricChange(publication, checkpoint, field, event.target.value)
                }
                placeholder="0"
              />
            </label>
          ))}
        </div>
        <button
          type="button"
          className="insights-primary-button checkpoint-save"
          disabled={savingPublicationId === publication.publication_id}
          onClick={() => void saveMetrics(publication, checkpoint)}
        >
          {savingPublicationId === publication.publication_id ? "Saving..." : "Save checkpoint"}
        </button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="analytics-loading" role="status">
        <span className="spinner large" />
        <span>Gathering your performance story...</span>
      </div>
    );
  }

  const pillarMax = Math.max(1, ...(dashboard?.pillar_performance ?? []).map((item) => item.impressions));

  return (
    <div className="insights-workspace">
      <header className="insights-hero">
        <div className="insights-hero-copy">
          <span className="insights-kicker"><Sparkles size={14} /> THE BIG PICTURE</span>
          <h1>Your work, <em>in motion.</em></h1>
          <p>A clear view of what is resonating, what is growing, and where to go next.</p>
          {loadError && <div className="insights-error" role="alert">{loadError}</div>}
        </div>
        <div className="insights-hero-art" aria-hidden="true">
          <span className="insights-orbit orbit-one" />
          <span className="insights-orbit orbit-two" />
          <span className="insights-orbit orbit-three" />
          <span className="insights-orbit-core"><BarChart3 size={31} /></span>
          <span className="insights-spark spark-one">✦</span>
          <span className="insights-spark spark-two">✧</span>
          <span className="insights-spark spark-three">✦</span>
        </div>
        <div className="insights-tabs" role="tablist" aria-label="Analytics views">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "dashboard"}
            className={activeTab === "dashboard" ? "active" : ""}
            onClick={() => setActiveTab("dashboard")}
          >
            <BarChart3 size={15} /> Overview
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "experiments"}
            className={activeTab === "experiments" ? "active" : ""}
            onClick={() => setActiveTab("experiments")}
          >
            <FlaskConical size={15} /> Experiments
          </button>
        </div>
      </header>

      {activeTab === "dashboard" ? (
        <div className="insights-content">
          <section className="insight-stat-grid" aria-label="Performance totals">
            <article className="insight-stat-card impressions">
              <div className="insight-stat-top">
                <span className="insight-stat-icon"><Eye size={18} /></span>
                <span className="insight-stat-label">Total impressions</span>
                <span className="insight-stat-index">01</span>
              </div>
              <strong>{number(dashboard?.total_impressions)}</strong>
              <span className="insight-stat-caption">Across tracked content</span>
              <span className="insight-stat-decoration" aria-hidden="true">↗</span>
            </article>
            <article className="insight-stat-card reactions">
              <div className="insight-stat-top">
                <span className="insight-stat-icon"><Heart size={18} /></span>
                <span className="insight-stat-label">Total reactions</span>
                <span className="insight-stat-index">02</span>
              </div>
              <strong>{number(dashboard?.total_reactions)}</strong>
              <span className="insight-stat-caption">A little love goes a long way</span>
              <span className="insight-stat-decoration" aria-hidden="true">✳</span>
            </article>
            <article className="insight-stat-card posts">
              <div className="insight-stat-top">
                <span className="insight-stat-icon"><MessageCircle size={18} /></span>
                <span className="insight-stat-label">Top posts</span>
                <span className="insight-stat-index">03</span>
              </div>
              <strong>{number(dashboard?.top_posts?.length)}</strong>
              <span className="insight-stat-caption">Pieces leading the conversation</span>
              <span className="insight-stat-decoration" aria-hidden="true">✦</span>
            </article>
          </section>

          <div className="insights-main-grid">
            <section className="insight-panel pillar-panel">
              <div className="insight-panel-heading">
                <div>
                  <span className="insight-panel-kicker">WHAT'S RESONATING</span>
                  <h2>Content pillars</h2>
                </div>
                <span className="insight-panel-icon"><BarChart3 size={18} /></span>
              </div>
              {dashboard?.pillar_performance.length ? (
                <div className="pillar-chart">
                  {dashboard.pillar_performance.map((pillar, index) => (
                    <div className="pillar-row" key={pillar.name}>
                      <div className="pillar-row-label">
                        <span className={`pillar-dot dot-${index % 4}`} />
                        <strong>{pillar.name}</strong>
                        <span>{number(pillar.impressions)} views</span>
                      </div>
                      <div className="pillar-track">
                        <span
                          className={`pillar-fill fill-${index % 4}`}
                          style={{ width: `${Math.max(4, (pillar.impressions / pillarMax) * 100)}%` }}
                        />
                      </div>
                      <span className="pillar-reactions">
                        <Heart size={13} /> {number(pillar.reactions)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="insights-empty">
                  <div><BarChart3 size={20} /></div>
                  <strong>Your story starts here</strong>
                  <span>Once you log post metrics, your strongest themes will appear here.</span>
                </div>
              )}
            </section>

            <section className="insight-panel top-posts-panel">
              <div className="insight-panel-heading">
                <div>
                  <span className="insight-panel-kicker">COMMUNITY FAVORITES</span>
                  <h2>Top performing</h2>
                </div>
                <span className="insight-panel-icon accent"><Sparkles size={18} /></span>
              </div>
              {dashboard?.top_posts.length ? (
                <div className="top-post-list">
                  {dashboard.top_posts.slice(0, 5).map((post, index) => (
                    <article className="top-post-row" key={`${post.platform_post_id}-${index}`}>
                      <span className={`top-post-number tone-${index % 4}`}>{String(index + 1).padStart(2, "0")}</span>
                      <div className="top-post-copy">
                        <strong>{post.title || "Untitled post"}</strong>
                        <span>{post.platform} · {number(post.impressions)} impressions</span>
                      </div>
                      <div className="top-post-reactions">
                        <Heart size={14} /> {number(post.reactions)}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="insights-empty compact">
                  <strong>No top posts just yet</strong>
                  <span>Add metrics below to see your best-performing content.</span>
                </div>
              )}
              <div className="insight-tip">
                <Sparkles size={14} />
                <span>Consistency compounds. Keep showing up with your strongest ideas.</span>
              </div>
            </section>
          </div>

          <section className="checkpoint-dashboard-controls" aria-label="Analytics filters">
            <label>
              Compare checkpoint
              <select
                value={selectedCheckpoint}
                onChange={(event) => {
                  const value = event.target.value as MetricCheckpoint;
                  setSelectedCheckpoint(value);
                  void fetchDashboard(value, selectedPlatform);
                }}
              >
                {checkpoints.map((checkpoint) => (
                  <option key={checkpoint} value={checkpoint}>
                    {checkpointLabels[checkpoint]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Platform
              <select
                value={selectedPlatform}
                onChange={(event) => {
                  const value = event.target.value as "all" | Platform;
                  setSelectedPlatform(value);
                  void fetchDashboard(selectedCheckpoint, value);
                }}
              >
                <option value="all">All platforms</option>
                <option value="x">X</option>
                <option value="linkedin">LinkedIn</option>
              </select>
            </label>
            <span>Totals and comparisons use only the selected checkpoint.</span>
          </section>

          {(["x", "linkedin"] as const).map((platform) => (
            <section className="insight-panel publication-metrics-panel" key={platform}>
              <div className="insight-panel-heading manual-log-heading">
                <div>
                  <span className="insight-panel-kicker">POST-BY-POST RESULTS</span>
                  <h2>Your recent {platform === "x" ? "X" : "LinkedIn"} posts</h2>
                  <p>Up to 20 newest published posts. Save or correct figures at each checkpoint.</p>
                </div>
                <button
                  type="button"
                  className="insights-outline-button"
                  onClick={() => {
                    setArchiveSearch("");
                    setArchiveQuery("");
                    void loadArchive(platform, 0, "");
                  }}
                >
                  View all {platform === "x" ? "X" : "LinkedIn"} posts
                </button>
              </div>
              {recentPosts[platform].length ? (
                <div className="metric-post-grid">
                  {recentPosts[platform].map((post, index) => (
                    <article className="metric-post-card" key={post.publication_id}>
                      <div className={`metric-post-art art-${index % 4}`}>
                        <span>{platform.toUpperCase()} / POST {String(index + 1).padStart(2, "0")}</span>
                        <Sparkles size={19} aria-hidden="true" />
                      </div>
                      <div className="metric-post-body">
                        <h3>{post.title || "Untitled post"}</h3>
                        <span className="metric-post-date">
                          Published {shortDate(post.published_at)}
                        </span>
                        {post.platform_post_url && (
                          <a
                            className="publication-view-link"
                            href={post.platform_post_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            View published post <ArrowUpRight size={12} />
                          </a>
                        )}
                        {renderMetricEditor(post)}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="insights-empty metric-empty">
                  <div><MessageCircle size={20} /></div>
                  <strong>No published {platform === "x" ? "X" : "LinkedIn"} posts found</strong>
                  <span>Published posts will appear here so you can add checkpoint metrics.</span>
                </div>
              )}
            </section>
          ))}
          {metricsStatus && (
            <p className="insights-feedback success" role="status">{metricsStatus}</p>
          )}
        </div>
      ) : (
        <section className="experiments-section">
          <div className="experiments-intro">
            <div className="experiments-intro-mark"><FlaskConical size={23} /></div>
            <div>
              <span className="insight-panel-kicker">TEST, LEARN, REFINE</span>
              <h2>Small experiments. Smarter decisions.</h2>
              <p>Compare variants and let your audience show you what works.</p>
            </div>
          </div>
          {experiments.length ? (
            <div className="experiment-grid">
              {experiments.map((experiment, index) => (
                <article className={`experiment-card experiment-tone-${index % 3}`} key={experiment.id}>
                  <div className="experiment-card-top">
                    <span className="experiment-number">EXPERIMENT {String(index + 1).padStart(2, "0")}</span>
                    <span className={`experiment-status ${experiment.status}`}>
                      <span />{experiment.status}
                    </span>
                  </div>
                  <h3>{experiment.name}</h3>
                  <p className="experiment-hypothesis">{experiment.hypothesis}</p>
                  <div className="experiment-dates">
                    <span>Started {shortDate(experiment.start_date)}</span>
                    {experiment.end_date && <span>Ends {shortDate(experiment.end_date)}</span>}
                  </div>
                  <div className="experiment-variants">
                    {Object.entries(experiment.metrics || {}).length ? (
                      Object.entries(experiment.metrics || {}).map(([variant, metrics]) => (
                        <div className="experiment-variant" key={variant}>
                          <strong>Variant {variant}</strong>
                          <span><Eye size={13} /> {number(metrics.impressions)}</span>
                          <span><Heart size={13} /> {number(metrics.reactions)}</span>
                          <span>{number(metrics.posts)} posts</span>
                        </div>
                      ))
                    ) : (
                      <p>No variant results have been recorded yet.</p>
                    )}
                  </div>
                  <span className="experiment-card-watermark" aria-hidden="true"><FlaskConical size={74} /></span>
                </article>
              ))}
            </div>
          ) : (
            <div className="experiments-empty">
              <div><FlaskConical size={24} /></div>
              <h3>Your next insight starts with a test.</h3>
              <p>No active experiments yet. Set up a content experiment to compare what resonates.</p>
              <span>Experiments are created from the Content workspace.</span>
              <ArrowUpRight size={15} aria-hidden="true" />
            </div>
          )}
        </section>
      )}
      {archivePlatform && archivePage && (
        <div className="analytics-modal-backdrop">
          <section
            className="analytics-archive-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="analytics-archive-title"
          >
            <div className="analytics-modal-heading">
              <div>
                <span className="insight-panel-kicker">PUBLISHED POSTS</span>
                <h2 id="analytics-archive-title">
                  All {archivePlatform === "x" ? "X" : "LinkedIn"} posts
                </h2>
                <p>{archivePage.total} publications. Select a title to edit its measurements.</p>
              </div>
              <button
                type="button"
                className="analytics-modal-close"
                aria-label="Close published posts"
                onClick={() => {
                  setArchivePlatform(null);
                  setArchivePage(null);
                }}
              >
                <X size={19} />
              </button>
            </div>
            <form
              className="analytics-archive-search"
              onSubmit={(event) => {
                event.preventDefault();
                setArchiveQuery(archiveSearch);
                void loadArchive(archivePlatform, 0, archiveSearch);
              }}
            >
              <label>
                <Search size={15} />
                <input
                  type="search"
                  value={archiveSearch}
                  placeholder="Search post titles"
                  onChange={(event) => setArchiveSearch(event.target.value)}
                />
              </label>
              <button type="submit" className="insights-outline-button">Search</button>
            </form>
            <div className="analytics-publication-list">
              {archivePage.items.map((publication) => (
                <button
                  type="button"
                  className="analytics-publication-list-item"
                  key={publication.publication_id}
                  onClick={() => {
                    setSelectedPublication(publication);
                    setActiveCheckpoints((current) => ({
                      ...current,
                      [publication.publication_id]:
                        current[publication.publication_id] ??
                        defaultCheckpoint(publication),
                    }));
                  }}
                >
                  <span>
                    <strong>{publication.title || "Untitled post"}</strong>
                    <small>Published {shortDate(publication.published_at)}</small>
                  </span>
                  <ChevronRight size={17} />
                </button>
              ))}
              {!archivePage.items.length && (
                <p className="analytics-no-results">No published posts match this search.</p>
              )}
            </div>
            <div className="analytics-pagination">
              <span>
                {archivePage.total
                  ? `${archivePage.offset + 1}–${Math.min(
                      archivePage.offset + archivePage.items.length,
                      archivePage.total,
                    )} of ${archivePage.total}`
                  : "0 posts"}
              </span>
              <div>
                <button
                  type="button"
                  className="secondary-button small"
                  disabled={archiveOffset === 0}
                  onClick={() =>
                    void loadArchive(
                      archivePlatform,
                      Math.max(0, archiveOffset - 50),
                      archiveQuery,
                    )
                  }
                >
                  <ChevronLeft size={14} /> Previous
                </button>
                <button
                  type="button"
                  className="secondary-button small"
                  disabled={archiveOffset + 50 >= archivePage.total}
                  onClick={() =>
                    void loadArchive(
                      archivePlatform,
                      archiveOffset + 50,
                      archiveQuery,
                    )
                  }
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </section>
        </div>
      )}
      {selectedPublication && (
        <div className="analytics-modal-backdrop analytics-detail-backdrop">
          <section
            className="analytics-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="analytics-detail-title"
          >
            <div className="analytics-modal-heading">
              <div>
                <span className="insight-panel-kicker">
                  {selectedPublication.platform.toUpperCase()} · POST METRICS
                </span>
                <h2 id="analytics-detail-title">{selectedPublication.title}</h2>
                <p>Published {shortDate(selectedPublication.published_at)}</p>
              </div>
              <button
                type="button"
                className="analytics-modal-close"
                aria-label="Close post metrics"
                onClick={() => setSelectedPublication(null)}
              >
                <X size={19} />
              </button>
            </div>
            {selectedPublication.platform_post_url && (
              <a
                className="publication-view-link"
                href={selectedPublication.platform_post_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                View published post <ArrowUpRight size={12} />
              </a>
            )}
            {renderMetricEditor(selectedPublication)}
          </section>
        </div>
      )}
    </div>
  );
}
