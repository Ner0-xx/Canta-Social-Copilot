import { Lightbulb, Sparkles, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";
import { generateDraftsForIdea, generateIdeas, getIdeas, getSourceItems } from "../lib/api";
import type { ContentIdeaData, SourceItemData } from "../types";

export function IdeasWorkspace() {
  const [ideas, setIdeas] = useState<ContentIdeaData[]>([]);
  const [sourceItems, setSourceItems] = useState<SourceItemData[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatingDraftId, setGeneratingDraftId] = useState<number | null>(null);

  const [selectedSourceId, setSelectedSourceId] = useState<number | "">("");
  const [customTopic, setCustomTopic] = useState("");
  const [customContent, setCustomContent] = useState("");
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    try {
      const [ideasList, itemsList] = await Promise.all([getIdeas(), getSourceItems()]);
      setIdeas(ideasList);
      setSourceItems(itemsList);
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to load ideas",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleGenerateIdeas = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenerating(true);
    setNotice(null);

    try {
      const newIdeas = await generateIdeas({
        source_item_id: selectedSourceId ? Number(selectedSourceId) : undefined,
        topic_title: customTopic.trim() || undefined,
        topic_content: customContent.trim() || undefined,
      });

      setNotice({
        type: "success",
        text: `Generated ${newIdeas.length} new AI content ideas!`,
      });
      setCustomTopic("");
      setCustomContent("");
      await loadData();
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to generate ideas",
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateDrafts = async (ideaId: number) => {
    setGeneratingDraftId(ideaId);
    setNotice(null);
    try {
      const drafts = await generateDraftsForIdea(ideaId);
      setNotice({
        type: "success",
        text: `Generated ${drafts.length} post variants (X Post, X Thread, LinkedIn). Check the Content tab!`,
      });
      await loadData();
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to generate drafts",
      });
    } finally {
      setGeneratingDraftId(null);
    }
  };

  if (loading) {
    return <div className="workspace-card">Loading idea inbox...</div>;
  }

  return (
    <div className="workspace-container">
      <header className="workspace-header">
        <div>
          <h2>Source-Backed Content Ideas</h2>
          <p>Generate, score, and select strategic content angles aligned with your brand voice and pillars.</p>
        </div>
      </header>

      {notice && (
        <div className={`notice ${notice.type}`}>
          <span>{notice.text}</span>
        </div>
      )}

      {/* AI Idea Generator Form */}
      <div className="workspace-card">
        <h3>
          <Sparkles size={18} /> AI Content Idea Generator
        </h3>
        <form onSubmit={(e) => void handleGenerateIdeas(e)} className="form-group">
          <div className="grid-2">
            <label>
              Select Ingested Material
              <select
                value={selectedSourceId}
                onChange={(e) => setSelectedSourceId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">-- Custom Topic / Manual Prompt --</option>
                {sourceItems.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title} ({item.author})
                  </option>
                ))}
              </select>
            </label>

            <label>
              Custom Topic Title (Optional)
              <input
                type="text"
                placeholder="e.g., Local AI Workflows vs Cloud APIs"
                value={customTopic}
                onChange={(e) => setCustomTopic(e.target.value)}
                disabled={Boolean(selectedSourceId)}
              />
            </label>
          </div>

          {!selectedSourceId && (
            <label>
              Additional Context / Key Insights
              <textarea
                rows={2}
                placeholder="Paste key takeaways, statistics, or angles you want the model to analyze..."
                value={customContent}
                onChange={(e) => setCustomContent(e.target.value)}
              />
            </label>
          )}

          <button type="submit" className="primary-button" disabled={generating}>
            {generating ? "Brainstorming Ideas..." : "Generate Strategic Ideas"}
          </button>
        </form>
      </div>

      {/* Idea Inbox List */}
      <section className="workspace-card margin-top">
        <h3>
          <Lightbulb size={18} /> Strategic Idea Inbox ({ideas.length})
        </h3>
        {ideas.length === 0 ? (
          <p className="empty-state">No content ideas created yet. Use the generator above to create your first ideas.</p>
        ) : (
          <div className="idea-list">
            {ideas.map((idea) => (
              <div key={idea.id} className="idea-card">
                <div className="idea-header">
                  <h4>{idea.title}</h4>
                  <div className="badge-group">
                    <span className="relevance-badge">
                      Score: {idea.relevance_score.toFixed(1)}%
                    </span>
                    <span className={`status-tag ${idea.status}`}>{idea.status}</span>
                  </div>
                </div>

                <p className="summary">{idea.summary}</p>
                {idea.proposed_angle && (
                  <div className="angle-box">
                    <strong>Hook / Takeaway Angle:</strong> {idea.proposed_angle}
                  </div>
                )}

                <div className="idea-footer">
                  <span className="source-ref">Source: {idea.source_ref || idea.source_type}</span>
                  <button
                    type="button"
                    className="primary-button small"
                    onClick={() => void handleGenerateDrafts(idea.id)}
                    disabled={generatingDraftId === idea.id}
                  >
                    <Wand2 size={14} />
                    {generatingDraftId === idea.id ? "Drafting..." : "Generate X & LinkedIn Drafts"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
