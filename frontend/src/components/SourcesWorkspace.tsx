import { BookOpenText, Link2, Plus, RefreshCw, Rss } from "lucide-react";
import { useEffect, useState } from "react";
import { createSource, getSourceItems, getSources, syncSource } from "../lib/api";
import type { SourceData, SourceItemData } from "../types";

export function SourcesWorkspace() {
  const [sources, setSources] = useState<SourceData[]>([]);
  const [items, setItems] = useState<SourceItemData[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [syncingId, setSyncingId] = useState<number | null>(null);

  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState<"rss" | "url" | "note">("rss");
  const [uriOrContent, setUriOrContent] = useState("");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    try {
      const [srcList, itemList] = await Promise.all([getSources(), getSourceItems()]);
      setSources(srcList);
      setItems(itemList);
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to load sources",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uriOrContent.trim()) return;

    setSubmitting(true);
    setMessage(null);
    try {
      await createSource({
        name: name.trim() || sourceType.toUpperCase(),
        source_type: sourceType,
        uri_or_content: uriOrContent.trim(),
      });
      setName("");
      setUriOrContent("");
      setMessage({ type: "success", text: "Source added and ingested successfully." });
      await loadData();
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to add source",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSync = async (id: number) => {
    setSyncingId(id);
    try {
      await syncSource(id);
      setMessage({ type: "success", text: "Source synced successfully." });
      await loadData();
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Sync failed",
      });
    } finally {
      setSyncingId(null);
    }
  };

  if (loading) {
    return <div className="workspace-card">Loading sources...</div>;
  }

  return (
    <div className="workspace-container">
      <header className="workspace-header">
        <div>
          <h2>Research & Ingestion Sources</h2>
          <p>Connect RSS feeds, paste article URLs, or store raw notes to fuel source-backed content generation.</p>
        </div>
      </header>

      {message && (
        <div className={`notice ${message.type}`}>
          <span>{message.text}</span>
        </div>
      )}

      <div className="card-grid">
        {/* Add Source Form */}
        <div className="workspace-card">
          <h3>
            <Plus size={18} /> Add New Source
          </h3>
          <form onSubmit={(e) => void handleAddSource(e)} className="form-group">
            <label>
              Source Type
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value as "rss" | "url" | "note")}
              >
                <option value="rss">RSS / Atom Feed URL</option>
                <option value="url">Web Page URL</option>
                <option value="note">Raw Text Note</option>
              </select>
            </label>

            <label>
              Label / Name (Optional)
              <input
                type="text"
                placeholder="e.g., TechCrunch AI RSS or Product Strategy Notes"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>

            <label>
              {sourceType === "note" ? "Note Content" : "URL / Feed Endpoint"}
              {sourceType === "note" ? (
                <textarea
                  rows={4}
                  placeholder="Paste research notes, insights, or document takeaways here..."
                  value={uriOrContent}
                  onChange={(e) => setUriOrContent(e.target.value)}
                  required
                />
              ) : (
                <input
                  type="url"
                  placeholder={sourceType === "rss" ? "https://example.com/feed.xml" : "https://example.com/article"}
                  value={uriOrContent}
                  onChange={(e) => setUriOrContent(e.target.value)}
                  required
                />
              )}
            </label>

            <button type="submit" className="primary-button" disabled={submitting}>
              {submitting ? "Ingesting..." : "Add Source"}
            </button>
          </form>
        </div>

        {/* Active Sources List */}
        <div className="workspace-card">
          <h3>
            <BookOpenText size={18} /> Active Sources ({sources.length})
          </h3>
          {sources.length === 0 ? (
            <p className="empty-state">No sources added yet. Add an RSS feed or note to get started.</p>
          ) : (
            <div className="item-list">
              {sources.map((src) => (
                <div key={src.id} className="source-item-card">
                  <div className="source-meta">
                    {src.source_type === "rss" ? <Rss size={16} /> : <Link2 size={16} />}
                    <strong>{src.name}</strong>
                    <span className={`status-tag ${src.status}`}>{src.status}</span>
                  </div>
                  <p className="source-url">{src.uri_or_content}</p>
                  <div className="card-actions">
                    <button
                      type="button"
                      className="secondary-button icon-btn"
                      onClick={() => void handleSync(src.id)}
                      disabled={syncingId === src.id}
                    >
                      <RefreshCw size={14} className={syncingId === src.id ? "spin" : ""} /> Sync
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Ingested Items Inbox */}
      <section className="workspace-card margin-top">
        <h3>Ingested Material Inbox ({items.length})</h3>
        {items.length === 0 ? (
          <p className="empty-state">No items ingested yet. Ingested RSS articles and notes will appear here.</p>
        ) : (
          <div className="ingested-items-grid">
            {items.map((item) => (
              <div key={item.id} className="ingested-card">
                <h4>{item.title}</h4>
                <div className="ingested-meta">
                  <span>{item.author || "Web Source"}</span> •{" "}
                  <time>{new Date(item.ingested_at).toLocaleDateString()}</time>
                </div>
                <p className="snippet">{item.content.substring(0, 180)}...</p>
                {item.url && (
                  <a href={item.url} target="_blank" rel="noreferrer" className="link-text">
                    View Source Link →
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
