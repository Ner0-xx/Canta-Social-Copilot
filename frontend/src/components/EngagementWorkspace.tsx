import { MessageSquare, Bot, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { request } from "../lib/api";
import type { DraftReplyData, EngagementInboxItem } from "../types";

export function EngagementWorkspace() {
  const [inbox, setInbox] = useState<EngagementInboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [draftingId, setDraftingId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    const fetchInbox = async () => {
      try {
        const data = await request<EngagementInboxItem[]>("/api/engagement/inbox");
        setInbox(data);
      } catch (err) {
        console.error("Failed to load inbox", err);
      } finally {
        setLoading(false);
      }
    };
    void fetchInbox();
  }, []);

  const handleDraftReply = async (comment: EngagementInboxItem) => {
    setDraftingId(comment.id);
    try {
      const response = await request<DraftReplyData>("/api/engagement/draft-reply", {
        method: "POST",
        body: JSON.stringify({
          comment_content: comment.content,
          post_title: comment.post_title,
          tone: "professional and insightful"
        })
      });
      setDrafts(prev => ({...prev, [comment.id]: response.draft_reply}));
    } catch {
      alert("Failed to draft reply");
    } finally {
      setDraftingId(null);
    }
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
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 bg-teal-100 text-teal-600 rounded-xl">
            <MessageSquare className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">Engagement & Inbox</h1>
            <p className="text-gray-500">Draft context-aware replies to your audience</p>
          </div>
        </div>

        <div className="space-y-6">
          {inbox.length === 0 ? (
            <div className="text-center p-12 bg-white rounded-2xl border border-gray-200">
              <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">Inbox Zero</h3>
              <p className="text-gray-500">You're all caught up on comments.</p>
            </div>
          ) : (
            inbox.map((comment) => (
              <div key={comment.id} className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-gray-100">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600 capitalize mb-2">
                        {comment.platform}
                      </span>
                      <p className="text-sm font-medium text-gray-500">On post: "{comment.post_title}"</p>
                    </div>
                  </div>
                  <div className="flex gap-4 items-start">
                    <div className="w-10 h-10 rounded-full bg-gray-200 flex-shrink-0 flex items-center justify-center font-bold text-gray-500">
                      {comment.author[0]}
                    </div>
                    <div>
                      <p className="font-bold text-gray-900">{comment.author}</p>
                      <p className="text-gray-700 mt-1">{comment.content}</p>
                    </div>
                  </div>
                </div>
                
                <div className="p-5 bg-gray-50">
                  {drafts[comment.id] ? (
                    <div className="space-y-3">
                      <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                        <Bot size={16} className="text-teal-600" />
                        AI Suggested Reply
                      </label>
                      <textarea
                        className="w-full h-24 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-transparent resize-none text-sm"
                        value={drafts[comment.id]}
                        onChange={(e) => setDrafts({...drafts, [comment.id]: e.target.value})}
                      />
                      <div className="flex justify-end gap-3">
                        <button 
                          className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 rounded-lg"
                          onClick={() => {
                            const newDrafts = {...drafts};
                            delete newDrafts[comment.id];
                            setDrafts(newDrafts);
                          }}
                        >
                          Discard
                        </button>
                        <button className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 shadow-sm">
                          <Send size={16} />
                          Publish Reply
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleDraftReply(comment)}
                      disabled={draftingId === comment.id}
                      className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 shadow-sm disabled:opacity-50"
                    >
                      {draftingId === comment.id ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900" />
                      ) : (
                        <Bot size={16} className="text-teal-600" />
                      )}
                      Draft AI Reply
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
