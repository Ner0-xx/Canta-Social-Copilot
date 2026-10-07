import { AlertCircle, CheckCircle2, Linkedin, RefreshCw, Settings, Unlink } from "lucide-react";
import { useEffect, useState } from "react";
import { getOAuthStatus, connectOAuth, disconnectOAuth } from "../lib/api";
import type { OAuthConnectionData } from "../types";

type Platform = "linkedin" | "x";

export function SettingsWorkspace() {
  const [linkedinStatus, setLinkedinStatus] = useState<OAuthConnectionData | null>(null);
  const [xStatus, setXStatus] = useState<OAuthConnectionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshingStatus, setRefreshingStatus] = useState(false);
  const [statusError, setStatusError] = useState(false);
  const [disconnectingPlatform, setDisconnectingPlatform] = useState<Platform | null>(null);
  const [urlMessage, setUrlMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const refreshStatuses = async () => {
    const [linkedinResult, xResult] = await Promise.allSettled([
      getOAuthStatus("linkedin"),
      getOAuthStatus("x"),
    ]);

    setLinkedinStatus(linkedinResult.status === "fulfilled" ? linkedinResult.value : null);
    setXStatus(xResult.status === "fulfilled" ? xResult.value : null);
    setStatusError(linkedinResult.status === "rejected" || xResult.status === "rejected");
  };

  const handleRefreshStatuses = async () => {
    setRefreshingStatus(true);
    try {
      await refreshStatuses();
    } finally {
      setRefreshingStatus(false);
    }
  };

  const handleDisconnect = async (platform: Platform) => {
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
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("success")) {
      const platform = urlParams.get("platform");
      const platformName = platform === "x" ? "X" : "LinkedIn";
      setUrlMessage({ type: "success", text: `${platformName} connected successfully.` });
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
      <div className="settings-loading" role="status" aria-label="Loading account connections">
        <span className="spinner large" />
        <span>Checking your social accounts...</span>
      </div>
    );
  }

  const accounts: Array<{
    platform: Platform;
    name: string;
    description: string;
    status: OAuthConnectionData | null;
  }> = [
    {
      platform: "linkedin",
      name: "LinkedIn",
      description: "Connect your LinkedIn account to publish posts directly.",
      status: linkedinStatus,
    },
    {
      platform: "x",
      name: "X",
      description: "Connect your X account to publish posts directly.",
      status: xStatus,
    },
  ];

  return (
    <div className="settings-workspace">
      <header className="settings-heading">
        <div className="settings-heading-icon">
          <Settings size={24} aria-hidden="true" />
        </div>
        <div>
          <p className="settings-eyebrow">Workspace settings</p>
          <h1>Social accounts</h1>
          <p className="settings-description">View and manage your LinkedIn and X connections.</p>
        </div>
      </header>

      {urlMessage && (
        <div
          role={urlMessage.type === "success" ? "status" : "alert"}
          className={`settings-message ${urlMessage.type}`}
        >
          {urlMessage.type === "success" ? (
            <CheckCircle2 size={19} aria-hidden="true" />
          ) : (
            <AlertCircle size={19} aria-hidden="true" />
          )}
          <span>{urlMessage.text}</span>
        </div>
      )}

      {statusError && (
        <div role="alert" className="settings-message warning">
          <AlertCircle size={19} aria-hidden="true" />
          <span>We couldn’t verify one or more account connections. Try checking again.</span>
          <button
            type="button"
            onClick={() => void handleRefreshStatuses()}
            disabled={refreshingStatus}
            className="settings-retry-button"
          >
            <RefreshCw size={15} className={refreshingStatus ? "is-spinning" : undefined} aria-hidden="true" />
            {refreshingStatus ? "Checking..." : "Check again"}
          </button>
        </div>
      )}

      <section className="settings-integrations" aria-labelledby="integrations-title">
        <div className="settings-section-heading">
          <div>
            <h2 id="integrations-title">Connected platforms</h2>
            <p>Each account is managed independently. Disconnecting won’t delete your social account.</p>
          </div>
          <span className="settings-account-count">{accounts.length} platforms</span>
        </div>

        <div className="settings-account-list">
          {accounts.map(({ platform, name, description, status }) => {
            const connected = status?.connected === true;
            const statusUnavailable = status === null && statusError;
            const isDisconnecting = disconnectingPlatform === platform;

            return (
              <article
                key={platform}
                className={`settings-account-card${connected ? " connected" : ""}`}
                aria-label={`${name} account`}
              >
                <div className={`settings-platform-icon ${platform}`} aria-hidden="true">
                  {platform === "linkedin" ? <Linkedin size={25} /> : <span>X</span>}
                </div>

                <div className="settings-account-details">
                  <div className="settings-account-title">
                    <h3>{platform === "x" ? "X" : name}</h3>
                    {connected ? (
                      <span className="settings-status-badge connected">
                        <CheckCircle2 size={14} aria-hidden="true" />
                        Connected
                      </span>
                    ) : statusUnavailable ? (
                      <span className="settings-status-badge unavailable">
                        <AlertCircle size={14} aria-hidden="true" />
                        Status unavailable
                      </span>
                    ) : (
                      <span className="settings-status-badge disconnected">Not connected</span>
                    )}
                  </div>

                  <p className="settings-account-description">
                    {connected ? (
                      <>
                        {platform === "x" ? "X" : "LinkedIn"} account:{" "}
                        <strong>
                          {status.account_name || (platform === "x" ? "X User" : "LinkedIn User")}
                        </strong>
                      </>
                    ) : description}
                  </p>

                  {connected && status.token_expired && (
                    <p className="settings-expiry-warning">
                      Access has expired. Reconnect this account to publish.
                    </p>
                  )}
                  {connected && !status.token_expired && status.expires_at && (
                    <p className="settings-expiry">
                      Access active until {new Date(status.expires_at).toLocaleDateString()}
                    </p>
                  )}
                </div>

                <div className="settings-account-action">
                  {connected ? (
                    <button
                      type="button"
                      onClick={() => void handleDisconnect(platform)}
                      disabled={disconnectingPlatform !== null}
                      className="settings-disconnect-button"
                    >
                      <Unlink size={16} aria-hidden="true" />
                      {isDisconnecting ? "Disconnecting..." : "Disconnect"}
                    </button>
                  ) : statusUnavailable ? null : (
                    <button
                      type="button"
                      onClick={() => connectOAuth(platform)}
                      className={`settings-connect-button ${platform}`}
                    >
                      Connect account
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
