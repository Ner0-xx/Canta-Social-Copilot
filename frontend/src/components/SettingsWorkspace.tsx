import { Settings, Linkedin, CheckCircle2, AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { getOAuthStatus, connectOAuth } from "../lib/api";
import type { OAuthConnectionData } from "../types";

export function SettingsWorkspace() {
  const [linkedinStatus, setLinkedinStatus] = useState<OAuthConnectionData | null>(null);
  const [xStatus, setXStatus] = useState<OAuthConnectionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [urlMessage, setUrlMessage] = useState<{type: "success" | "error", text: string} | null>(null);

  useEffect(() => {
    // Check URL for OAuth callback messages
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("success")) {
      setUrlMessage({ type: "success", text: "Successfully connected to LinkedIn!" });
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (urlParams.get("error")) {
      setUrlMessage({ type: "error", text: `Failed to connect: ${urlParams.get("error")}` });
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    const checkStatus = async () => {
      try {
        const [li, x] = await Promise.all([
          getOAuthStatus("linkedin"),
          getOAuthStatus("x")
        ]);
        setLinkedinStatus(li);
        setXStatus(x);
      } catch (err) {
        console.error("Failed to fetch OAuth status", err);
      } finally {
        setLoading(false);
      }
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
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${urlMessage.type === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
            {urlMessage.type === "success" ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
            <span>{urlMessage.text}</span>
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
                  {linkedinStatus?.connected && linkedinStatus.expires_at && (
                     <div className="flex items-center gap-1.5 mt-2">
                       <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                       <p className="text-xs font-medium text-green-700">
                         Active until {new Date(linkedinStatus.expires_at).toLocaleDateString()}
                       </p>
                     </div>
                  )}
                </div>
              </div>
              
              <div>
                {linkedinStatus?.connected ? (
                  <button 
                    className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg font-medium shadow-sm cursor-default"
                    disabled
                  >
                    <CheckCircle2 size={18} />
                    <span>Connected</span>
                  </button>
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
                  {xStatus?.connected && xStatus.expires_at && (
                     <div className="flex items-center gap-1.5 mt-2">
                       <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                       <p className="text-xs font-medium text-green-700">
                         Active until {new Date(xStatus.expires_at).toLocaleDateString()}
                       </p>
                     </div>
                  )}
                </div>
              </div>
              
              <div>
                {xStatus?.connected ? (
                  <button 
                    className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg font-medium shadow-sm cursor-default"
                    disabled
                  >
                    <CheckCircle2 size={18} />
                    <span>Connected</span>
                  </button>
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
