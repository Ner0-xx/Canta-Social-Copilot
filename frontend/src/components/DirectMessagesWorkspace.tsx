import { AlertCircle, Inbox, MessageCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { request } from "../lib/api";
import type { XDirectMessagesData } from "../types";

function formatDate(value?: string) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function DirectMessagesWorkspace() {
  const [data, setData] = useState<XDirectMessagesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadInbox = async () => {
    setError(null);
    try {
      setData(await request<XDirectMessagesData>("/api/engagement/x/direct-messages"));
    } catch (requestError) {
      setData(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not load X direct messages.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void loadInbox();
  }, []);

  if (loading) {
    return (
      <div className="engagement-loading" role="status">
        <span className="spinner large" />
        <span>Loading X direct messages...</span>
      </div>
    );
  }

  return (
    <div className="engagement-workspace dm-workspace">
      <header className="engagement-header">
        <div className="engagement-heading">
          <div className="engagement-heading-icon">
            <Inbox size={23} aria-hidden="true" />
          </div>
          <div>
            <p className="engagement-eyebrow">Private conversations</p>
            <h1>X inbox</h1>
            <p className="engagement-subtitle">
              Direct messages are separate from public posts and mentions.
            </p>
          </div>
        </div>
        <button
          type="button"
          className="engagement-refresh"
          onClick={() => {
            setRefreshing(true);
            void loadInbox();
          }}
          disabled={refreshing}
        >
          <RefreshCw
            size={15}
            className={refreshing ? "is-spinning" : undefined}
            aria-hidden="true"
          />
          {refreshing ? "Loading..." : "Refresh inbox"}
        </button>
      </header>

      <div className="dm-account-bar">
        <span className="dm-live-indicator" />
        {data
          ? `Connected as @${data.account.username}`
          : error
            ? "Inbox unavailable. See the provider error above."
            : "Connect an X account in Settings to view your inbox."}
        <span className="dm-history-note">View-only inbox</span>
        <span className="dm-history-note">Showing up to the latest 100 message events from X</span>
      </div>

      {error && (
        <div className="engagement-error" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <span>{error}</span>
          <button
            type="button"
            onClick={() => {
              setRefreshing(true);
              void loadInbox();
            }}
            disabled={refreshing}
          >
            Try again
          </button>
        </div>
      )}

      {!error && data?.conversations.length === 0 && (
        <div className="dm-empty-state">
          <div><MessageCircle size={23} aria-hidden="true" /></div>
          <h2>No recent direct messages</h2>
          <p>X returned no message events for this account.</p>
        </div>
      )}

      {data?.conversations.length ? (
        <div className="dm-conversation-list">
          {data.conversations.map((conversation) => (
            <section className="dm-conversation-card" key={conversation.id}>
              <header>
                <span className="dm-avatar">
                  {conversation.participant.trim().charAt(0).toUpperCase() || "?"}
                </span>
                <div>
                  <h2>{conversation.participant}</h2>
                  {conversation.participant_username && (
                    <span>@{conversation.participant_username}</span>
                  )}
                </div>
                <span className="dm-message-count">
                  {conversation.messages.length}{" "}
                  {conversation.messages.length === 1 ? "message" : "messages"}
                </span>
              </header>
              <div className="dm-message-list">
                {conversation.messages.map((message) => (
                  <article
                    className={message.is_me ? "dm-message mine" : "dm-message"}
                    key={message.id}
                  >
                    <div className="dm-message-meta">
                      <strong>{message.is_me ? "You" : message.sender_name}</strong>
                      <time>{formatDate(message.created_at)}</time>
                    </div>
                    <p>{message.text || "This message does not contain text."}</p>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}
