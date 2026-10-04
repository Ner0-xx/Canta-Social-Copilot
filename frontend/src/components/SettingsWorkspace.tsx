import { Settings, Linkedin, CheckCircle2, AlertCircle, Unlink } from "lucide-react";
import { useEffect, useState } from "react";
import { getOAuthStatus, connectOAuth, disconnectOAuth } from "../lib/api";
import type { OAuthConnectionData } from "../types";

export function SettingsWorkspace() {
  const [linkedinStatus, setLinkedinStatus] = useState<OAuthConnectionData | null>(null);
  const [xStatus, setXStatus] = useState<OAuthConnectionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshingStatus, setRefreshingStatus] = useState(false);
  const [statusError, setStatusError] = useState(false);
  const [disconnectingPlatform, setDisconnectingPlatform] = useState<string | null>(null);
  const [urlMessage, setUrlMessage] = useState<{type: "success" | "error", text: string} | null>(null);

  const refreshStatuses = async () => {
    const [li, x] = await Promise.allSettled([
      getOAuthStatus("linkedin"),
      getOAuthStatus("x"),
    ]);
    setLinkedinStatus(li.status === "fulfilled" ? li.value : null);
    setXStatus(x.status === "fulfilled" ? x.value : null);
    setStatusError(li.status === "rejected" || x.status === "rejected");
  };

  const handleRefreshStatuses = async () => {
    setRefreshingStatus(true);
    await refreshStatuses();
    setRefreshingStatus(false);
  };

  const handleDisconnect = async (platform: "linkedin" | "x") => {
    const platformName = platform === "linkedin" ? "LinkedIn" : "X";
    if (!window.confirm(`Disconnect your ${platformName} account from this app?`)) return;

    setDisconnectingPlatform(platform);
    setUrlMessage(null);
    try {
      await disconnectOAuth(platform);
      await refreshStatuses();
      setUrlMessage({ type: "success", text: `${platformName} has been disconnected from this app.` });
    } catch (err) {
      setUrlMessage({
        type: "error",
        text: err instanceof Error ? err.message : `Could not disconnect ${platformName}.`,
      });
    } finally {
      setDisconnectingPlatform(null);
    }
  };

  useEffect(() => {
    // Check URL for OAuth callback messages
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("success")) {
      const platform = urlParams.get("platform");
      const platformName = platform === "x" ? "X" : "LinkedIn";
      setUrlMessage({ type: "success", text: `${platformName} connected successfully.` });
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (urlParams.get("error")) {
      setUrlMessage({ type: "error", text: `Failed to connect: ${urlParams.get("error")}` });
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    const checkStatus = async () => {
      await refreshStatuses();
      setLoading(false);
    };

    void checkStatus();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-gray-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 text-gray-900 flex flex-col items-center">
      <div className="w-full max-w-4xl p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-xl shadow-sm">
            <Settings className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Settings & Integrations
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              Manage your connections to external platforms
            </p>
          </div>
        </div>

        {urlMessage && (
          <div role="status" className={`mb-6 p-4 rounded-lg flex items-center gap-2 border ${urlMessage.type === "success" ? "bg-green-50 text-green-800 border-green-200" : "bg-red-50 text-red-800 border-red-200"}`}>
            {urlMessage.type === "success" ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
            <span>{urlMessage.text}</span>
          </div>
        )}

        {statusError && (
          <div role="alert" className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <span>We couldn’t verify one or more account connections. Your connection may still be saved.</span>
            <button
              type="button"
              onClick={() => void handleRefreshStatuses()}
              disabled={refreshingStatus}
              className="rounded-md border border-amber-300 bg-white px-3 py-1.5 font-medium text-amber-900 hover:bg-amber-100 disabled:opacity-60"
            >
              {refreshingStatus ? "Checking..." : "Check again"}
            </button>
          </div>
        )}

        <div className="space-y-6">
          <section className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <h2 className="text-xl font-bold mb-4 border-b pb-2">Social Integrations</h2>
            
            <div className={`flex items-center justify-between p-5 border rounded-xl transition-all duration-300 ${linkedinStatus?.connected ? 'border-green-200 bg-green-50/40 shadow-sm' : 'border-gray-200 hover:border-blue-300 hover:shadow-md bg-white'}`}>
              <div className="flex items-center gap-5">
                <div className={`w-14 h-14 rounded-xl flex items-center justify-center text-white transition-transform duration-300 hover:scale-105 shadow-sm ${linkedinStatus?.connected ? 'bg-gradient-to-br from-[#0077b5] to-[#005582]' : 'bg-[#0077b5]'}`}>
                  <Linkedin size={28} />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-900">LinkedIn</h3>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {linkedinStatus?.connected 
                      ? `Connected as ${linkedinStatus.account_name || "LinkedIn User"}` 
                      : "Connect your LinkedIn account to publish posts directly."}
                  </p>
                  {linkedinStatus?.connected && (
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-800">
                        <CheckCircle2 size={14} /> Connected
                      </span>
                      {linkedinStatus.token_expired ? (
                        <span className="text-xs font-medium text-amber-800">Access expired; reconnect to publish</span>
                      ) : linkedinStatus.expires_at ? (
                        <span className="text-xs text-gray-500">Access active until {new Date(linkedinStatus.expires_at).toLocaleDateString()}</span>
                      ) : null}
                    </div>
                  )}
                </div>
              </div>
              
              <div>
                {linkedinStatus?.connected ? (
                  <button
                    type="button"
                    onClick={() => void handleDisconnect("linkedin")}
                    disabled={disconnectingPlatform !== null}
                    className="flex items-center gap-2 px-4 py-2.5 border border-red-200 text-red-700 rounded-lg font-medium hover:bg-red-50 disabled:opacity-60 disabled:cursor-wait transition-colors"
                  >
                    <Unlink size={16} />
                    <span>{disconnectingPlatform === "linkedin" ? "Disconnecting..." : "Disconnect"}</span>
                  </button>
                ) : linkedinStatus === null && statusError ? (
                  <span className="text-sm font-medium text-amber-800">Status unavailable</span>
                ) : (
                  <button 
                    onClick={() => connectOAuth("linkedin")}
                    className="px-6 py-2.5 bg-[#0077b5] text-white rounded-lg font-medium shadow-sm hover:bg-[#005582] hover:shadow-md transition-all active:scale-95"
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>

            <div className={`flex items-center justify-between p-5 border rounded-xl transition-all duration-300 mt-4 ${xStatus?.connected ? 'border-green-200 bg-green-50/40 shadow-sm' : 'border-gray-200 hover:border-gray-400 hover:shadow-md bg-white'}`}>
              <div className="flex items-center gap-5">
                <div className={`w-14 h-14 rounded-xl flex items-center justify-center text-white font-bold text-3xl transition-transform duration-300 hover:scale-105 shadow-sm ${xStatus?.connected ? 'bg-gradient-to-br from-gray-900 to-black' : 'bg-black'}`}>
                  X
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-900">X (Twitter)</h3>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {xStatus?.connected 
                      ? `Connected as ${xStatus.account_name || "X User"}` 
                      : "Connect your X account to publish posts directly."}
                  </p>
                  {xStatus?.connected && (
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-800">
                        <CheckCircle2 size={14} /> Connected
                      </span>
                      {xStatus.token_expired ? (
                        <span className="text-xs font-medium text-amber-800">Access expired; reconnect to publish</span>
                      ) : xStatus.expires_at ? (
                        <span className="text-xs text-gray-500">Access active until {new Date(xStatus.expires_at).toLocaleDateString()}</span>
                      ) : null}
                    </div>
                  )}
                </div>
              </div>
              
              <div>
                {xStatus?.connected ? (
                  <button
                    type="button"
                    onClick={() => void handleDisconnect("x")}
                    disabled={disconnectingPlatform !== null}
                    className="flex items-center gap-2 px-4 py-2.5 border border-red-200 text-red-700 rounded-lg font-medium hover:bg-red-50 disabled:opacity-60 disabled:cursor-wait transition-colors"
                  >
                    <Unlink size={16} />
                    <span>{disconnectingPlatform === "x" ? "Disconnecting..." : "Disconnect"}</span>
                  </button>
                ) : xStatus === null && statusError ? (
                  <span className="text-sm font-medium text-amber-800">Status unavailable</span>
                ) : (
                  <button 
                    onClick={() => connectOAuth("x")}
                    className="px-6 py-2.5 bg-black text-white rounded-lg font-medium shadow-sm hover:bg-gray-800 hover:shadow-md transition-all active:scale-95"
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
