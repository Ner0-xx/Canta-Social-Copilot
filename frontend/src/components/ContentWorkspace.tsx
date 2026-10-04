import { AlertTriangle, CheckCircle2, Copy, ShieldCheck, Image as ImageIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { CalendarDays, Send } from "lucide-react";
import { checkDraftQuality, getDrafts, updateDraftStatus, scheduleDraft, publishManual, updateDraft, uploadDraftImage, getExperiments } from "../lib/api";
import type { ContentDraftData, AABExperimentData } from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export function ContentWorkspace() {
  const [drafts, setDrafts] = useState<ContentDraftData[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterPlatform, setFilterPlatform] = useState<string>("all");
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editBody, setEditBody] = useState("");
  const [scheduleTime, setScheduleTime] = useState("");
  const [uploadingId, setUploadingId] = useState<number | null>(null);
  const [experiments, setExperiments] = useState<AABExperimentData[]>([]);
  const [editExperimentId, setEditExperimentId] = useState<number | undefined>();
  const [editExperimentVariant, setEditExperimentVariant] = useState<string>("");

  const loadDrafts = async () => {
    try {
      const [list, exps] = await Promise.all([getDrafts(), getExperiments()]);
      setDrafts(list);
      setExperiments(exps);
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to load drafts",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDrafts();
  }, []);

  const handleStatusChange = async (draftId: number, status: string) => {
    try {
      await updateDraftStatus(draftId, status);
      setNotice({ type: "success", text: `Draft status updated to ${status}.` });
      await loadDrafts();
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to update status",
      });
    }
  };

  const handleRecheckQuality = async (draftId: number) => {
    try {
      const res = await checkDraftQuality(draftId);
      setNotice({
        type: "success",
        text: `Quality score updated: ${(res.score * 100).toFixed(0)}%`,
      });
      await loadDrafts();
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed quality check",
      });
    }
  };

  const handleCopyClipboard = (draft: ContentDraftData) => {
    navigator.clipboard.writeText(draft.body);
    setCopiedId(draft.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSaveEdit = async (draftId: number) => {
    try {
      await updateDraft(draftId, { 
        body: editBody,
        experiment_id: editExperimentId,
        experiment_variant: editExperimentVariant || undefined,
      });
      setNotice({ type: "success", text: "Draft updated successfully." });
      setEditingId(null);
      await loadDrafts();
    } catch {
      setNotice({ type: "error", text: "Failed to update draft." });
    }
  };

  const handleSchedule = async (draft: ContentDraftData) => {
    if (!scheduleTime) {
      setNotice({ type: "error", text: "Please select a date and time." });
      return;
    }
    const d = new Date(scheduleTime);
    if (isNaN(d.getTime())) {
      setNotice({ type: "error", text: "Invalid date selected." });
      return;
    }
    try {
      await scheduleDraft(draft.id, draft.platform, d.toISOString());
      setNotice({ type: "success", text: "Draft scheduled successfully." });
      setScheduleTime("");
      await loadDrafts();
    } catch {
      setNotice({ type: "error", text: "Failed to schedule draft." });
    }
  };

  const handleManualPublish = async (draftId: number) => {
    try {
      await publishManual(draftId);
      setNotice({ type: "success", text: "Draft marked as manually published." });
      await loadDrafts();
    } catch {
      setNotice({ type: "error", text: "Failed to publish manually." });
    }
  };

  const handleImageUpload = async (draftId: number, file: File) => {
    try {
      setUploadingId(draftId);
      await uploadDraftImage(draftId, file);
      setNotice({ type: "success", text: "Image uploaded successfully." });
      await loadDrafts();
    } catch {
      setNotice({ type: "error", text: "Failed to upload image." });
    } finally {
      setUploadingId(null);
    }
  };

  const filteredDrafts = drafts.filter((d) => {
    if (filterPlatform === "all") return true;
    return d.platform.toLowerCase() === filterPlatform;
  });

  if (loading) {
    return <div className="workspace-card">Loading content drafts...</div>;
  }

  return (
    <div className="workspace-container">
      <header className="workspace-header">
        <div>
          <h2>Content Studio & Quality Control</h2>
          <p>Review side-by-side post variants for X and LinkedIn with real-time quality & safety compliance checks.</p>
        </div>
      </header>

      {notice && (
        <div className={`notice ${notice.type}`}>
          <span>{notice.text}</span>
        </div>
      )}

      {/* Platform Filter Tabs */}
      <div className="tab-bar">
        <button
          type="button"
          className={filterPlatform === "all" ? "tab-button active" : "tab-button"}
          onClick={() => setFilterPlatform("all")}
        >
          All Drafts ({drafts.length})
        </button>
        <button
          type="button"
          className={filterPlatform === "x" ? "tab-button active" : "tab-button"}
          onClick={() => setFilterPlatform("x")}
        >
          X (Twitter) Variants ({drafts.filter((d) => d.platform === "x").length})
        </button>
        <button
          type="button"
          className={filterPlatform === "linkedin" ? "tab-button active" : "tab-button"}
          onClick={() => setFilterPlatform("linkedin")}
        >
          LinkedIn Variants ({drafts.filter((d) => d.platform === "linkedin").length})
        </button>
      </div>

      {filteredDrafts.length === 0 ? (
        <div className="workspace-card margin-top">
          <p className="empty-state">No drafts found. Generate drafts from the Ideas tab to get started.</p>
        </div>
      ) : (
        <div className="draft-grid margin-top">
          {filteredDrafts.map((draft) => (
            <div key={draft.id} className="draft-card">
              <div className="draft-header">
                <div className="platform-tag font-bold">
                  {draft.platform.toUpperCase()} • {draft.variant_type.toUpperCase()}
                </div>
                <div className="badge-group">
                  <span
                    className={`score-badge ${
                      draft.quality_score >= 0.8 ? "pass" : "warn"
                    }`}
                  >
                    Quality: {(draft.quality_score * 100).toFixed(0)}%
                  </span>
                  <span className={`status-tag ${draft.status}`}>{draft.status}</span>
                </div>
              </div>

              <h4 className="draft-title">{draft.title}</h4>
              <div className="draft-body-box">
                {editingId === draft.id ? (
                  <div className="flex flex-col gap-2">
                    <textarea 
                      className="w-full h-32 p-2 border rounded-md"
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                    />
                    
                    {experiments.length > 0 && (
                      <div className="flex gap-2">
                        <select 
                          className="p-1 border rounded"
                          value={editExperimentId || ""}
                          onChange={(e) => setEditExperimentId(Number(e.target.value) || undefined)}
                        >
                          <option value="">No Experiment</option>
                          {experiments.map(exp => (
                            <option key={exp.id} value={exp.id}>{exp.name}</option>
                          ))}
                        </select>
                        <select
                          className="p-1 border rounded"
                          value={editExperimentVariant}
                          onChange={(e) => setEditExperimentVariant(e.target.value)}
                        >
                          <option value="">Variant...</option>
                          <option value="A">Variant A</option>
                          <option value="B">Variant B</option>
                        </select>
                      </div>
                    )}
                    
                    <div className="flex gap-2">
                      <button className="primary-button small" onClick={() => void handleSaveEdit(draft.id)}>Save</button>
                      <button className="secondary-button small" onClick={() => setEditingId(null)}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <pre>{draft.body}</pre>
                    {draft.experiment_id && (
                      <div className="mt-2 text-xs bg-purple-100 text-purple-800 p-1 rounded inline-block">
                        🧪 Experiment: {experiments.find(e => e.id === draft.experiment_id)?.name} ({draft.experiment_variant})
                      </div>
                    )}
                    {draft.image_path && (
                      <div className="mt-4 mb-2 rounded-lg overflow-hidden border border-gray-200">
                        <img 
                          src={`${API_BASE_URL}${draft.image_path}`} 
                          alt="Draft attachment" 
                          className="w-full object-cover max-h-64"
                        />
                      </div>
                    )}
                    <button 
                      className="text-blue-500 text-xs mt-2 underline"
                      onClick={() => {
                        setEditingId(draft.id);
                        setEditBody(draft.body);
                        setEditExperimentId(draft.experiment_id);
                        setEditExperimentVariant(draft.experiment_variant || "");
                      }}
                    >
                      Edit Draft
                    </button>
                  </>
                )}
              </div>

              {/* Quality Warnings */}
              {draft.warnings && draft.warnings.length > 0 && (
                <div className="warnings-box">
                  <AlertTriangle size={15} />
                  <div>
                    {draft.warnings.map((w, idx) => (
                      <p key={idx}>{w}</p>
                    ))}
                  </div>
                </div>
              )}

              {/* Card Footer Actions */}
              <div className="card-actions-bar">
                <button
                  type="button"
                  className="secondary-button small"
                  onClick={() => handleCopyClipboard(draft)}
                >
                  <Copy size={13} /> {copiedId === draft.id ? "Copied!" : "Copy to Clipboard"}
                </button>

                <button
                  type="button"
                  className="secondary-button small"
                  onClick={() => void handleRecheckQuality(draft.id)}
                >
                  <ShieldCheck size={13} /> Check Quality
                </button>
                
                <label className="secondary-button small cursor-pointer">
                  <input 
                    type="file" 
                    accept="image/*" 
                    className="hidden" 
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleImageUpload(draft.id, file);
                    }}
                  />
                  <ImageIcon size={13} /> {uploadingId === draft.id ? "Uploading..." : "Add Image"}
                </label>

                {draft.status === "draft" && (
                  <button
                    type="button"
                    className="primary-button small"
                    onClick={() => void handleStatusChange(draft.id, "in_review")}
                  >
                    Submit for Review
                  </button>
                )}

                {draft.status === "in_review" && (
                  <>
                    <button
                      type="button"
                      className="primary-button small approve-btn"
                      onClick={() => void handleStatusChange(draft.id, "approved")}
                    >
                      <CheckCircle2 size={13} /> Approve
                    </button>
                    <button
                      type="button"
                      className="secondary-button small"
                      onClick={() => void handleStatusChange(draft.id, "rejected")}
                    >
                      Reject
                    </button>
                  </>
                )}

                {draft.status === "approved" && (
                  <>
                    <div className="flex gap-2 items-center ml-auto">
                      <input 
                        type="datetime-local" 
                        className="text-xs p-1 border rounded"
                        value={scheduleTime}
                        onChange={(e) => setScheduleTime(e.target.value)}
                      />
                      <button
                        type="button"
                        className="primary-button small"
                        onClick={() => void handleSchedule(draft)}
                      >
                        <CalendarDays size={13} /> Schedule
                      </button>
                      <button
                        type="button"
                        className="secondary-button small"
                        onClick={() => void handleManualPublish(draft.id)}
                      >
                        <Send size={13} /> Manual Publish
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
