import {
  Activity,
  BarChart3,
  BookOpenText,
  CalendarDays,
  CircleHelp,
  FilePenLine,
  Inbox,
  LayoutDashboard,
  Menu,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

import { CalendarWorkspace } from "./components/CalendarWorkspace";
import { SettingsWorkspace } from "./components/SettingsWorkspace";
import { ContentWorkspace } from "./components/ContentWorkspace";
import { IdeasWorkspace } from "./components/IdeasWorkspace";
import { SourcesWorkspace } from "./components/SourcesWorkspace";
import { StrategyWorkspace } from "./components/StrategyWorkspace";
import { AnalyticsWorkspace } from "./components/AnalyticsWorkspace";
import { EngagementWorkspace } from "./components/EngagementWorkspace";
import { DirectMessagesWorkspace } from "./components/DirectMessagesWorkspace";
import { Brand } from "./components/Brand";
import { Login } from "./components/Login";
import { useAuth } from "./components/auth-context";
import { getSettings, getStrategy, saveSettings, saveStrategy } from "./lib/api";
import {
  emptyStrategy,
  type AppSettings,
  type ReleaseLevel,
  type Strategy,
} from "./types";

const releaseLevels: Array<{ value: ReleaseLevel; label: string }> = [
  { value: "observe", label: "Observe" },
  { value: "draft", label: "Draft" },
  { value: "approve", label: "Approve" },
  { value: "integrate", label: "Integrate" },
  { value: "schedule", label: "Schedule" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<"strategy" | "sources" | "ideas" | "content" | "calendar" | "engagement" | "inbox" | "analytics" | "settings">(() =>
    window.location.pathname.replace(/\/$/, "") === "/settings" ? "settings" : "strategy",
  );
  const [strategy, setStrategy] = useState<Strategy>(emptyStrategy);
  const [settings, setSettings] = useState<AppSettings>({
    release_level: "observe",
    publishing_enabled: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(
    null,
  );
  const { session, signOut } = useAuth();

  useEffect(() => {
    if (!session) return;
    
    Promise.all([getStrategy(), getSettings()])
      .then(([strategyData, settingsData]) => {
        setStrategy(strategyData);
        setSettings(settingsData);
      })
      .catch((error: Error) => setNotice({ type: "error", text: error.message }))
      .finally(() => setLoading(false));
  }, [session]);

  const handleSave = async () => {
    setSaving(true);
    setNotice(null);
    try {
      const saved = await saveStrategy(strategy);
      setStrategy(saved);
      setNotice({ type: "success", text: "Strategy saved." });
    } catch (error) {
      setNotice({
        type: "error",
        text: error instanceof Error ? error.message : "Unable to save strategy.",
      });
    } finally {
      setSaving(false);
    }
  };

  const updateReleaseLevel = async (releaseLevel: ReleaseLevel) => {
    const previous = settings;
    const next = { ...settings, release_level: releaseLevel };
    setSettings(next);
    try {
      setSettings(await saveSettings(next));
      setNotice({ type: "success", text: `Release level set to ${releaseLevel}.` });
    } catch (error) {
      setSettings(previous);
      setNotice({
        type: "error",
        text: error instanceof Error ? error.message : "Unable to update release level.",
      });
    }
  };

  const togglePublishing = async () => {
    const previous = settings;
    const next = { ...settings, publishing_enabled: !settings.publishing_enabled };
    setSettings(next);
    try {
      setSettings(await saveSettings(next));
      setNotice({
        type: "success",
        text: next.publishing_enabled
          ? "Publishing controls enabled."
          : "Publishing kill switch activated.",
      });
    } catch (error) {
      setSettings(previous);
      setNotice({
        type: "error",
        text: error instanceof Error ? error.message : "Unable to update publishing.",
      });
    }
  };

  if (!session) {
    return <Login />;
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <span className="spinner large" />
        <span>Loading workspace</span>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className={mobileNavOpen ? "sidebar open" : "sidebar"}>
        <div className="brand-mark">
          <Brand />
          <button
            className="icon-button mobile-close"
            type="button"
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close navigation"
          >
            <X size={19} />
          </button>
        </div>

        <nav className="main-nav">
          <NavItem icon={<LayoutDashboard size={18} />} label="Overview" disabled />
          <NavItem
            icon={<ShieldCheck size={18} />}
            label="Strategy"
            active={activeTab === "strategy"}
            onClick={() => {
              setActiveTab("strategy");
              setMobileNavOpen(false);
            }}
          />
          <NavItem
            icon={<BookOpenText size={18} />}
            label="Sources"
            active={activeTab === "sources"}
            onClick={() => {
              setActiveTab("sources");
              setMobileNavOpen(false);
            }}
          />
          <NavItem
            icon={<Sparkles size={18} />}
            label="Ideas"
            active={activeTab === "ideas"}
            onClick={() => {
              setActiveTab("ideas");
              setMobileNavOpen(false);
            }}
          />
          <NavItem
            icon={<FilePenLine size={18} />}
            label="Content"
            active={activeTab === "content"}
            onClick={() => {
              setActiveTab("content");
              setMobileNavOpen(false);
            }}
          />
          <NavItem
            icon={<CalendarDays size={18} />}
            label="Calendar"
            active={activeTab === "calendar"}
            onClick={() => {
              setActiveTab("calendar");
              setMobileNavOpen(false);
            }}
          />
          <NavItem
            icon={<Users size={18} />}
            label="Engagement"
            active={activeTab === "engagement"}
            onClick={() => {
              setActiveTab("engagement");
              setMobileNavOpen(false);
            }}
          />
          <NavItem
            icon={<Inbox size={18} />}
            label="X Inbox"
            active={activeTab === "inbox"}
            onClick={() => {
              setActiveTab("inbox");
              setMobileNavOpen(false);
            }}
          />
          <NavItem
            icon={<BarChart3 size={18} />}
            label="Analytics"
            active={activeTab === "analytics"}
            onClick={() => {
              setActiveTab("analytics");
              setMobileNavOpen(false);
            }}
          />
        </nav>

        <div className="sidebar-footer">
          <NavItem 
            icon={<Settings size={18} />} 
            label="Settings" 
            active={activeTab === "settings"}
            onClick={() => {
              setActiveTab("settings");
              setMobileNavOpen(false);
            }}
          />
          <NavItem icon={<CircleHelp size={18} />} label="Help" disabled />
        </div>
      </aside>

      {mobileNavOpen && (
        <button
          className="nav-scrim"
          type="button"
          onClick={() => setMobileNavOpen(false)}
          aria-label="Close navigation"
        />
      )}

      <div className="main-column">
        <header className="topbar">
          <button
            className="icon-button menu-button"
            type="button"
            onClick={() => setMobileNavOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>
          <div className="connection-state">
            <Activity size={16} />
            <span>Cloud workspace</span>
          </div>
          <div className="release-controls">
            <button 
              onClick={() => void signOut()} 
              className="text-xs text-gray-500 underline mr-4 hover:text-gray-900"
            >
              Sign out
            </button>
            <label htmlFor="release-level">Release level</label>
            <select
              id="release-level"
              value={settings.release_level}
              onChange={(event) =>
                void updateReleaseLevel(event.target.value as ReleaseLevel)
              }
            >
              {releaseLevels.map((level) => (
                <option value={level.value} key={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
            <label className="switch-control">
              <input
                type="checkbox"
                checked={settings.publishing_enabled}
                onChange={() => void togglePublishing()}
              />
              <span className="switch" />
              <span>
                {settings.publishing_enabled ? "Publishing enabled" : "Publishing blocked"}
              </span>
            </label>
          </div>
        </header>

        {notice && (
          <div className={`notice ${notice.type}`} role="status">
            <span>{notice.text}</span>
            <button
              className="icon-button"
              type="button"
              onClick={() => setNotice(null)}
              aria-label="Dismiss notification"
            >
              <X size={16} />
            </button>
          </div>
        )}

        <main>
          {activeTab === "strategy" && (
            <StrategyWorkspace
              strategy={strategy}
              saving={saving}
              onChange={setStrategy}
              onSave={() => void handleSave()}
            />
          )}
          {activeTab === "sources" && <SourcesWorkspace />}
          {activeTab === "ideas" && <IdeasWorkspace />}
          {activeTab === "content" && <ContentWorkspace />}
          {activeTab === "calendar" && <CalendarWorkspace />}
          {activeTab === "engagement" && <EngagementWorkspace />}
          {activeTab === "inbox" && <DirectMessagesWorkspace />}
          {activeTab === "analytics" && <AnalyticsWorkspace />}
          {activeTab === "settings" && <SettingsWorkspace />}
        </main>
      </div>
    </div>
  );
}

function NavItem({
  icon,
  label,
  active = false,
  disabled = false,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className={active ? "nav-item active" : "nav-item"}
      disabled={disabled}
      onClick={onClick}
    >
      {icon}
      <span>{label}</span>
      {disabled && <small>Soon</small>}
    </button>
  );
}
