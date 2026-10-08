import {
  ArrowDownToLine,
  ArrowUpRight,
  BarChart3,
  Eye,
  FileSpreadsheet,
  FlaskConical,
  Heart,
  MessageCircle,
  Repeat2,
  Sparkles,
  Upload,
} from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";

import { getExperiments, request } from "../lib/api";
import type {
  AABExperimentData,
  AnalyticsDashboardData,
  RecentPublicationData,
  RecentPublicationMetrics,
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

export function AnalyticsWorkspace() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "experiments">("dashboard");
  const [dashboard, setDashboard] = useState<AnalyticsDashboardData | null>(null);
  const [experiments, setExperiments] = useState<AABExperimentData[]>([]);
  const [recentPosts, setRecentPosts] = useState<RecentPublicationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<{ text: string; error: boolean } | null>(null);
  const [savingMetrics, setSavingMetrics] = useState(false);
  const [metricsStatus, setMetricsStatus] = useState<{ text: string; error: boolean } | null>(
    null,
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDashboard = async () => {
    setLoadError(null);
    try {
      const [dashboardData, posts, experimentData] = await Promise.all([
        request<AnalyticsDashboardData>("/api/analytics/dashboard"),
        request<RecentPublicationData[]>("/api/analytics/recent-publications?platform=x"),
        getExperiments(),
      ]);
      setDashboard(dashboardData);
      setRecentPosts(posts);
      setExperiments(experimentData);
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Unable to load analytics right now.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchDashboard();
  }, []);

  const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const apiBaseUrl = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("platform", "linkedin");
    setUploadStatus({ text: "Uploading your report...", error: false });
    try {
      const response = await fetch(`${apiBaseUrl}/api/analytics/import/csv`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? `Upload failed (${response.status}).`);
      }
      setUploadStatus({ text: "Import complete. Your dashboard is up to date.", error: false });
      await fetchDashboard();
    } catch (error) {
      setUploadStatus({
        text: error instanceof Error ? error.message : "Could not upload that CSV.",
        error: true,
      });
    } finally {
      event.target.value = "";
    }
  };

  const handleManualSave = async () => {
    setSavingMetrics(true);
    setMetricsStatus(null);
    const entries = recentPosts.map((post) => ({
      platform_post_id: post.platform_post_id,
      platform: "x",
      impressions: post.metrics.impressions,
      reactions: post.metrics.reactions,
      comments: post.metrics.comments,
      reposts: post.metrics.reposts,
      clicks: 0,
    }));

    try {
      await request("/api/analytics/import/manual", {
        method: "POST",
        body: JSON.stringify(entries),
      });
      setMetricsStatus({ text: "Your X metrics have been saved.", error: false });
      await fetchDashboard();
    } catch (error) {
      setMetricsStatus({
        text: error instanceof Error ? error.message : "Failed to save X metrics.",
        error: true,
      });
    } finally {
      setSavingMetrics(false);
    }
  };

  const handleMetricChange = (
    index: number,
    field: keyof RecentPublicationMetrics,
    value: string,
  ) => {
    setRecentPosts((posts) =>
      posts.map((post, postIndex) =>
        postIndex === index
          ? {
              ...post,
              metrics: { ...post.metrics, [field]: Math.max(0, Number.parseInt(value, 10) || 0) },
            }
          : post,
      ),
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

          <section className="insight-panel manual-log-panel">
            <div className="insight-panel-heading manual-log-heading">
              <div>
                <span className="insight-panel-kicker">MAKE THE NUMBERS COUNT</span>
                <h2>Your recent X posts</h2>
                <p>Capture performance by hand, then bring those insights into your strategy.</p>
              </div>
              <button
                type="button"
                className="insights-primary-button"
                onClick={() => void handleManualSave()}
                disabled={!recentPosts.length || savingMetrics}
              >
                <ArrowDownToLine size={15} />
                {savingMetrics ? "Saving..." : "Save metrics"}
              </button>
            </div>
            {recentPosts.length ? (
              <div className="metric-post-grid">
                {recentPosts.map((post, index) => (
                  <article className="metric-post-card" key={`${post.platform_post_id}-${index}`}>
                    <div className={`metric-post-art art-${index % 4}`}>
                      <span>X / POST {String(index + 1).padStart(2, "0")}</span>
                      <Sparkles size={19} aria-hidden="true" />
                    </div>
                    <div className="metric-post-body">
                      <h3>{post.title || "Untitled post"}</h3>
                      <span className="metric-post-date">{shortDate(post.published_at)}</span>
                      <div className="metric-input-grid">
                        {([
                          ["impressions", "Views", Eye],
                          ["reactions", "Likes", Heart],
                          ["comments", "Comments", MessageCircle],
                          ["reposts", "Reposts", Repeat2],
                        ] as const).map(([field, label, Icon]) => (
                          <label className="metric-input" key={field}>
                            <span><Icon size={13} />{label}</span>
                            <input
                              type="number"
                              min="0"
                              value={post.metrics[field] || ""}
                              onChange={(event) => handleMetricChange(index, field, event.target.value)}
                              placeholder="0"
                            />
                          </label>
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="insights-empty metric-empty">
                <div><MessageCircle size={20} /></div>
                <strong>No recent X posts found to log</strong>
                <span>Publish a post and it will be available here for manual metric tracking.</span>
              </div>
            )}
            {metricsStatus && (
              <p className={`insights-feedback ${metricsStatus.error ? "error" : "success"}`} role="status">
                {metricsStatus.text}
              </p>
            )}
          </section>

          <section className="insight-import-banner">
            <div className="import-banner-icon"><FileSpreadsheet size={21} /></div>
            <div className="import-banner-copy">
              <span className="insight-panel-kicker">BRING YOUR DATA TOGETHER</span>
              <h2>Have a LinkedIn report?</h2>
              <p>Import a CSV export to bring your offline analytics into the picture.</p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              className="visually-hidden"
              accept=".csv"
              onChange={(event) => void handleFileUpload(event)}
            />
            <button
              type="button"
              className="insights-outline-button"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={15} /> Import CSV
            </button>
            {uploadStatus && (
              <p
                className={`insights-feedback ${uploadStatus.error ? "error" : "success"}`}
                role="status"
              >
                {uploadStatus.text}
              </p>
            )}
          </section>
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
    </div>
  );
}
