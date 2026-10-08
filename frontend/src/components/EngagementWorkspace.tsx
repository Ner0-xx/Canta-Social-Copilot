import {
  AlertCircle,
  ArrowUpRight,
  Bot,
  Check,
  Copy,
  Heart,
  Linkedin,
  MessageCircle,
  MessageSquareText,
  RefreshCw,
  Repeat2,
  Send,
  X as XIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { request } from "../lib/api";
import type { DraftReplyData, XEngagementData, XMention } from "../types";

function formatDate(value?: string) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function EngagementWorkspace() {
  const [data, setData] = useState<XEngagementData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [draftingId, setDraftingId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchData = async () => {
    setLoadError(null);
    try {
      setData(await request<XEngagementData>("/api/engagement/x?limit=20"));
    } catch (error) {
      setData(null);
      setLoadError(
        error instanceof Error ? error.message : "Could not load live X engagement.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const handleDraftReply = async (mention: XMention) => {
    setDraftingId(mention.id);
    setDraftError(null);
    try {
      const response = await request<DraftReplyData>("/api/engagement/draft-reply", {
        method: "POST",
        body: JSON.stringify({
          comment_content: mention.text,
          post_title: `X mention from @${mention.author.username ?? "user"}`,
          tone: "professional and insightful",
        }),
      });
      setDrafts((current) => ({ ...current, [mention.id]: response.draft_reply }));
    } catch (error) {
      setDraftError(
        error instanceof Error ? error.message : "Failed to draft a reply. Please try again.",
      );
    } finally {
      setDraftingId(null);
    }
  };

  const copyReply = async (id: string) => {
    try {
      await navigator.clipboard.writeText(drafts[id]);
      setCopiedId(id);
      window.setTimeout(() => setCopiedId((current) => (current === id ? null : current)), 1800);
    } catch {
      setDraftError("Could not copy the reply. Select and copy the text manually.");
    }
  };

  if (loading) {
    return (
      <div className="engagement-loading" role="status">
        <span className="spinner large" />
        <span>Loading live X engagement...</span>
      </div>
    );
  }

  return (
    <div className="engagement-workspace">
      <header className="engagement-header">
        <div className="engagement-heading">
          <div className="engagement-heading-icon">
            <MessageSquareText size={23} aria-hidden="true" />
          </div>
          <div>
            <p className="engagement-eyebrow">Community</p>
            <h1>Engagement</h1>
            <p className="engagement-subtitle">
              Live X posts and mentions, separated from your direct-message inbox.
            </p>
          </div>
        </div>
        <button
          type="button"
          className="engagement-refresh"
          onClick={() => {
            setRefreshing(true);
            void fetchData();
          }}
          disabled={refreshing}
        >
          <RefreshCw
            size={15}
            className={refreshing ? "is-spinning" : undefined}
            aria-hidden="true"
          />
          {refreshing ? "Loading..." : "Refresh"}
        </button>
      </header>

      {loadError && (
        <div className="engagement-error" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <span>{loadError}</span>
          <button
            type="button"
            onClick={() => {
              setRefreshing(true);
              void fetchData();
            }}
            disabled={refreshing}
          >
            Try again
          </button>
        </div>
      )}

      {draftError && (
        <div className="engagement-error" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <span>{draftError}</span>
          <button type="button" onClick={() => setDraftError(null)} aria-label="Dismiss reply error">
            <XIcon size={16} />
          </button>
        </div>
      )}

      <section className="engagement-platform x" aria-labelledby="engagement-x-title">
        <header className="engagement-platform-header">
          <div className="engagement-platform-mark x">
            <XIcon size={21} aria-hidden="true" />
          </div>
          <div className="engagement-platform-name">
            <h2 id="engagement-x-title">X</h2>
            <p>
              {data
                ? `Live activity for @${data.account.username}`
                : loadError
                  ? "X activity unavailable. See the provider error above."
                  : "Connect X in Settings to load account activity."}
            </p>
          </div>
          <span className="engagement-platform-count">
            {data ? `@${data.account.username}` : loadError ? "Unavailable" : "Not connected"}
          </span>
        </header>

        <div className="engagement-platform-columns">
          <section className="engagement-subsection" aria-labelledby="x-posts-title">
            <div className="engagement-subsection-heading">
              <div className="engagement-subsection-icon post">
                <ArrowUpRight size={16} aria-hidden="true" />
              </div>
              <div>
                <h3 id="x-posts-title">Your recent posts</h3>
                <p>Latest posts published by this X account</p>
              </div>
              <span className="engagement-subsection-count">{data?.posts.length ?? 0}</span>
            </div>
            {data?.posts.length ? (
              <div className="engagement-post-list">
                {data.posts.map((post) => (
                  <article className="engagement-live-post" key={post.id}>
                    <p>{post.text}</p>
                    <div className="engagement-live-post-meta">
                      <time>{formatDate(post.created_at)}</time>
                      {post.public_metrics && (
                        <span>
                          <Heart size={13} aria-hidden="true" />
                          {post.public_metrics.like_count ?? 0}
                          <Repeat2 size={13} aria-hidden="true" />
                          {post.public_metrics.repost_count ?? 0}
                          <MessageCircle size={13} aria-hidden="true" />
                          {post.public_metrics.reply_count ?? 0}
                        </span>
                      )}
                      {post.url && (
                        <a href={post.url} target="_blank" rel="noreferrer">
                          View on X <ArrowUpRight size={13} aria-hidden="true" />
                        </a>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="engagement-subsection-empty">
                {data ? "No recent posts were returned by X." : "Posts are unavailable until X is connected."}
              </div>
            )}
          </section>

          <section className="engagement-subsection" aria-labelledby="x-mentions-title">
            <div className="engagement-subsection-heading">
              <div className="engagement-subsection-icon inbox">
                <MessageCircle size={16} aria-hidden="true" />
              </div>
              <div>
                <h3 id="x-mentions-title">Mentions and replies</h3>
                <p>Posts that mention the connected X account</p>
              </div>
              <span className="engagement-subsection-count">{data?.mentions.length ?? 0}</span>
            </div>
            {data?.mentions.length ? (
              <div className="engagement-inbox-list">
                {data.mentions.map((mention) => (
                  <article className="engagement-item-card" key={mention.id}>
                    <div className="engagement-item-author">
                      <span className="engagement-avatar x">
                        {(mention.author.name ?? mention.author.username ?? "?")
                          .trim()
                          .charAt(0)
                          .toUpperCase()}
                      </span>
                      <div>
                        <strong>{mention.author.name ?? `@${mention.author.username ?? "user"}`}</strong>
                        <span>
                          @{mention.author.username ?? "unknown"} · {formatDate(mention.created_at)}
                        </span>
                      </div>
                    </div>
                    <p className="engagement-item-content">{mention.text}</p>
                    {mention.url && (
                      <a className="engagement-live-link" href={mention.url} target="_blank" rel="noreferrer">
                        Open mention on X <ArrowUpRight size={13} aria-hidden="true" />
                      </a>
                    )}
                    {drafts[mention.id] ? (
                      <div className="engagement-reply-editor">
                        <label htmlFor={`reply-${mention.id}`}>
                          <Bot size={15} aria-hidden="true" />
                          AI reply draft
                        </label>
                        <textarea
                          id={`reply-${mention.id}`}
                          value={drafts[mention.id]}
                          onChange={(event) =>
                            setDrafts((current) => ({ ...current, [mention.id]: event.target.value }))
                          }
                          rows={4}
                        />
                        <div className="engagement-reply-actions">
                          <span>Review before copying. Replies are not published from this screen.</span>
                          <button
                            type="button"
                            className="engagement-copy-button"
                            onClick={() => void copyReply(mention.id)}
                          >
                            {copiedId === mention.id ? <Check size={15} /> : <Copy size={15} />}
                            {copiedId === mention.id ? "Copied" : "Copy reply"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="engagement-draft-button"
                        onClick={() => void handleDraftReply(mention)}
                        disabled={draftingId === mention.id}
                      >
                        {draftingId === mention.id ? <span className="spinner" /> : <Send size={15} />}
                        {draftingId === mention.id ? "Writing reply..." : "Draft a reply"}
                      </button>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <div className="engagement-subsection-empty">
                {data ? "No recent mentions were returned by X." : "Mentions are unavailable until X is connected."}
              </div>
            )}
          </section>
        </div>
      </section>

      <section className="engagement-platform linkedin" aria-labelledby="engagement-linkedin-title">
        <header className="engagement-platform-header">
          <div className="engagement-platform-mark linkedin">
            <Linkedin size={21} aria-hidden="true" />
          </div>
          <div className="engagement-platform-name">
            <h2 id="engagement-linkedin-title">LinkedIn</h2>
            <p>LinkedIn publishing remains available in the Content workspace.</p>
          </div>
        </header>
        <div className="engagement-linkedin-note">
          The current LinkedIn connection grants publishing and profile access, not feed or inbox
          reading. LinkedIn does not currently provide this app the permissions needed to fetch
          your posts, comments, or direct messages.
        </div>
      </section>
    </div>
  );
}
