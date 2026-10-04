import { BarChart3, Upload } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { request, getExperiments } from "../lib/api";
import type {
  AABExperimentData,
  AnalyticsDashboardData,
  RecentPublicationData,
  RecentPublicationMetrics,
} from "../types";

export function AnalyticsWorkspace() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "experiments">("dashboard");
  const [dashboard, setDashboard] = useState<AnalyticsDashboardData | null>(null);
  const [experiments, setExperiments] = useState<AABExperimentData[]>([]);
  const [recentPosts, setRecentPosts] = useState<RecentPublicationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDashboard = async () => {
    try {
      const data = await request<AnalyticsDashboardData>("/api/analytics/dashboard");
      setDashboard(data);
      const posts = await request<RecentPublicationData[]>("/api/analytics/recent-publications?platform=x");
      setRecentPosts(posts);
      const exps = await getExperiments();
      setExperiments(exps);
    } catch (error) {
      console.error("Failed to load analytics", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchDashboard();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const apiBaseUrl = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("platform", "linkedin");

    setUploadStatus("Uploading...");
    try {
      const response = await fetch(`${apiBaseUrl}/api/analytics/import/csv`, {
        method: "POST",
        body: formData,
      });
      if (response.ok) {
        setUploadStatus("Success! Analytics updated.");
        await fetchDashboard();
      } else {
        setUploadStatus("Failed to upload.");
      }
    } catch {
      setUploadStatus("Error uploading file.");
    }

    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleManualSave = async () => {
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
      alert("Manual entries saved!");
      await fetchDashboard();
    } catch {
      alert("Failed to save entries");
    }
  };

  const handleMetricChange = (index: number, field: keyof RecentPublicationMetrics, value: string) => {
    setRecentPosts((posts) => posts.map((post, postIndex) =>
      postIndex === index
        ? { ...post, metrics: { ...post.metrics, [field]: Number.parseInt(value, 10) || 0 } }
        : post,
    ));
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 text-gray-900 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-indigo-100 text-indigo-600 rounded-xl">
              <BarChart3 className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-gray-900">Performance Analytics</h1>
              <p className="text-gray-500">Track and optimize your content strategy</p>
            </div>
          </div>
        </div>

        <div className="inline-flex rounded-xl border border-gray-200 bg-white p-1 shadow-sm mb-8">
          <button
            type="button"
            onClick={() => setActiveTab("dashboard")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "dashboard" ? "bg-indigo-600 text-white" : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Dashboard
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("experiments")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "experiments" ? "bg-indigo-600 text-white" : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Experiments
          </button>
        </div>

        {activeTab === "dashboard" && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
                <p className="text-sm font-medium text-gray-500 mb-1">Total Impressions</p>
                <h3 className="text-3xl font-bold text-gray-900">{dashboard?.total_impressions?.toLocaleString() || 0}</h3>
              </div>
              <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
                <p className="text-sm font-medium text-gray-500 mb-1">Total Engagements</p>
                <h3 className="text-3xl font-bold text-gray-900">{dashboard?.total_reactions?.toLocaleString() || 0}</h3>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
                <h2 className="text-lg font-bold mb-4">Top Performing Content</h2>
                <div className="space-y-4">
                  {dashboard?.top_posts?.length === 0 ? (
                    <p className="text-gray-500 text-sm">No data yet.</p>
                  ) : (
                    dashboard?.top_posts?.map((post, i) => (
                      <div key={i} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg border border-transparent hover:border-gray-100">
                        <div className="flex-1 min-w-0 pr-4">
                          <p className="text-sm font-medium text-gray-900 truncate">{post.title}</p>
                          <span className="text-xs text-gray-500 capitalize">{post.platform}</span>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold">{post.impressions?.toLocaleString()} views</p>
                          <p className="text-xs text-gray-500">{post.reactions?.toLocaleString()} likes</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col justify-between">
                <div>
                  <h2 className="text-lg font-bold mb-2">Import CSV Analytics</h2>
                  <p className="text-sm text-gray-500 mb-6">Upload your raw data exports from LinkedIn or X Premium to automatically populate your dashboard and inform your AI Strategy Engine.</p>
                </div>

                <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:bg-gray-50 transition-colors">
                  <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <div className="flex justify-center text-sm text-gray-600">
                    <label className="relative cursor-pointer rounded-md bg-white font-semibold text-blue-600 focus-within:outline-none focus-within:ring-2 focus-within:ring-blue-600 focus-within:ring-offset-2 hover:text-blue-500">
                      <span>Upload a file</span>
                      <input ref={fileInputRef} type="file" className="sr-only" accept=".csv" onChange={handleFileUpload} />
                    </label>
                    <p className="pl-1">or drag and drop</p>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">CSV up to 10MB</p>
                </div>
                {uploadStatus && (
                  <p className={`mt-4 text-sm font-medium ${uploadStatus.includes("Success") ? "text-green-600" : "text-blue-600"}`}>
                    {uploadStatus}
                  </p>
                )}
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">X (Twitter) Manual Log</h2>
                  <p className="text-sm text-gray-500">Quickly log impressions and likes for recent X posts if you don't have X Premium.</p>
                </div>
                <button
                  type="button"
                  onClick={handleManualSave}
                  className="px-4 py-2 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800 shadow-sm"
                >
                  Save Entries
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-500">
                  <thead className="bg-white text-xs uppercase text-gray-700 border-b">
                    <tr>
                      <th className="px-6 py-4 font-medium">Post Title</th>
                      <th className="px-6 py-4 font-medium">Published Date</th>
                      <th className="px-6 py-4 font-medium">Views</th>
                      <th className="px-6 py-4 font-medium">Likes</th>
                      <th className="px-6 py-4 font-medium">Comments</th>
                      <th className="px-6 py-4 font-medium">Reposts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentPosts.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                          No recent X posts found to log.
                        </td>
                      </tr>
                    ) : (
                      recentPosts.map((post, idx) => (
                        <tr key={idx} className="border-b hover:bg-gray-50">
                          <td className="px-6 py-4 font-medium text-gray-900 max-w-[200px] truncate">{post.title}</td>
                          <td className="px-6 py-4">{new Date(post.published_at).toLocaleDateString()}</td>
                          <td className="px-6 py-4">
                            <input
                              type="number"
                              className="w-20 border rounded p-1 text-sm"
                              value={post.metrics.impressions || ""}
                              onChange={(e) => handleMetricChange(idx, "impressions", e.target.value)}
                              placeholder="0"
                            />
                          </td>
                          <td className="px-6 py-4">
                            <input
                              type="number"
                              className="w-20 border rounded p-1 text-sm"
                              value={post.metrics.reactions || ""}
                              onChange={(e) => handleMetricChange(idx, "reactions", e.target.value)}
                              placeholder="0"
                            />
                          </td>
                          <td className="px-6 py-4">
                            <input
                              type="number"
                              className="w-20 border rounded p-1 text-sm"
                              value={post.metrics.comments || ""}
                              onChange={(e) => handleMetricChange(idx, "comments", e.target.value)}
                              placeholder="0"
                            />
                          </td>
                          <td className="px-6 py-4">
                            <input
                              type="number"
                              className="w-20 border rounded p-1 text-sm"
                              value={post.metrics.reposts || ""}
                              onChange={(e) => handleMetricChange(idx, "reposts", e.target.value)}
                              placeholder="0"
                            />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {activeTab === "experiments" && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Active Experiments</h2>
              {experiments.length === 0 ? (
                <p className="text-gray-500 text-sm">No active A/B experiments.</p>
              ) : (
                <div className="grid gap-6">
                  {experiments.map((exp) => (
                    <div key={exp.id} className="border border-gray-200 rounded-xl p-6">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-lg font-bold text-gray-900">{exp.name}</h3>
                          <p className="text-sm text-gray-500 mt-1">{exp.hypothesis}</p>
                        </div>
                        <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">
                          {exp.status.toUpperCase()}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        {Object.entries(exp.metrics || {}).map(([variant, metrics]) => (
                          <div key={variant} className="bg-gray-50 rounded-lg p-4">
                            <h4 className="font-semibold text-gray-900 mb-2 border-b pb-2">Variant {variant}</h4>
                            <div className="space-y-1 text-sm">
                              <p className="flex justify-between"><span className="text-gray-500">Posts:</span> <span className="font-medium">{metrics.posts}</span></p>
                              <p className="flex justify-between"><span className="text-gray-500">Impressions:</span> <span className="font-medium">{metrics.impressions.toLocaleString()}</span></p>
                              <p className="flex justify-between"><span className="text-gray-500">Reactions:</span> <span className="font-medium">{metrics.reactions.toLocaleString()}</span></p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
