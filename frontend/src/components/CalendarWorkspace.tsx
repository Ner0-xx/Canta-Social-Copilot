import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Layers3,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { cancelScheduledJob, getScheduledJobs } from "../lib/api";
import type { ScheduledJob } from "../types";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function dateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
    date.getDate(),
  ).padStart(2, "0")}`;
}

function jobDate(job: ScheduledJob) {
  return new Date(job.scheduled_at);
}

function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Time unavailable"
    : date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function CalendarWorkspace() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [month, setMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const [selectedDate, setSelectedDate] = useState(() => dateKey(new Date()));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const fetchJobs = async () => {
    setError(null);
    try {
      setJobs(await getScheduledJobs());
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not load your scheduled content.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchJobs();
  }, []);

  const monthCells = useMemo(() => {
    const firstDay = new Date(month.getFullYear(), month.getMonth(), 1);
    const mondayOffset = (firstDay.getDay() + 6) % 7;
    const gridStart = new Date(firstDay);
    gridStart.setDate(firstDay.getDate() - mondayOffset);
    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(gridStart);
      date.setDate(gridStart.getDate() + index);
      return date;
    });
  }, [month]);

  const jobsByDate = useMemo(() => {
    const grouped = new Map<string, ScheduledJob[]>();
    jobs.forEach((job) => {
      const key = dateKey(jobDate(job));
      grouped.set(key, [...(grouped.get(key) ?? []), job]);
    });
    return grouped;
  }, [jobs]);

  const selectedJobs = useMemo(
    () =>
      [...(jobsByDate.get(selectedDate) ?? [])].sort(
        (left, right) => jobDate(left).getTime() - jobDate(right).getTime(),
      ),
    [jobsByDate, selectedDate],
  );
  const pendingCount = jobs.filter((job) => job.status === "pending").length;
  const thisMonthCount = jobs.filter((job) => {
    const date = jobDate(job);
    return date.getFullYear() === month.getFullYear() && date.getMonth() === month.getMonth();
  }).length;

  const shiftMonth = (amount: number) => {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + amount, 1));
  };

  const handleCancel = async (id: number) => {
    setCancellingId(id);
    setError(null);
    try {
      await cancelScheduledJob(id);
      await fetchJobs();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not cancel this scheduled post.",
      );
    } finally {
      setCancellingId(null);
    }
  };

  if (loading) {
    return (
      <div className="calendar-loading" role="status">
        <span className="spinner large" />
        <span>Opening your publishing calendar...</span>
      </div>
    );
  }

  return (
    <div className="calendar-workspace">
      <header className="calendar-hero">
        <div className="calendar-hero-copy">
          <span className="calendar-kicker"><CalendarDays size={14} /> THE PUBLISHING RHYTHM</span>
          <h1>Make room for <em>what’s next.</em></h1>
          <p>A considered view of what is queued, when it goes live, and what’s coming up.</p>
        </div>
        <div className="calendar-hero-stats">
          <div>
            <span className="calendar-stat-icon"><Layers3 size={16} /></span>
            <strong>{pendingCount}</strong>
            <span>in the queue</span>
          </div>
          <div>
            <span className="calendar-stat-icon mint"><CalendarDays size={16} /></span>
            <strong>{thisMonthCount}</strong>
            <span>this month</span>
          </div>
        </div>
        <div className="calendar-hero-moon" aria-hidden="true">
          <span className="calendar-moon-ring ring-a" />
          <span className="calendar-moon-ring ring-b" />
          <span className="calendar-moon-core" />
          <span className="calendar-moon-star star-a">✦</span>
          <span className="calendar-moon-star star-b">✧</span>
        </div>
      </header>

      {error && <div className="calendar-error" role="alert">{error}</div>}

      <div className="calendar-content-grid">
        <section className="calendar-month-panel" aria-label="Monthly content calendar">
          <div className="calendar-month-header">
            <div>
              <span className="calendar-section-label">YOUR SCHEDULE</span>
              <h2>{month.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</h2>
            </div>
            <div className="calendar-month-controls">
              <button type="button" onClick={() => shiftMonth(-1)} aria-label="Previous month">
                <ArrowLeft size={17} />
              </button>
              <button
                type="button"
                className="calendar-today-button"
                onClick={() => {
                  const today = new Date();
                  setMonth(new Date(today.getFullYear(), today.getMonth(), 1));
                  setSelectedDate(dateKey(today));
                }}
              >
                Today
              </button>
              <button type="button" onClick={() => shiftMonth(1)} aria-label="Next month">
                <ArrowRight size={17} />
              </button>
            </div>
          </div>

          <div className="calendar-month-grid">
            {WEEKDAYS.map((day) => (
              <div className="calendar-weekday" key={day}>{day}</div>
            ))}
            {monthCells.map((date) => {
              const key = dateKey(date);
              const daysJobs = jobsByDate.get(key) ?? [];
              const isCurrentMonth = date.getMonth() === month.getMonth();
              const isToday = key === dateKey(new Date());
              const isSelected = key === selectedDate;
              return (
                <button
                  className={[
                    "calendar-day",
                    !isCurrentMonth && "outside",
                    isToday && "today",
                    isSelected && "selected",
                    daysJobs.length > 0 && "has-events",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={key}
                  type="button"
                  aria-label={`${date.toLocaleDateString()}, ${daysJobs.length} scheduled posts`}
                  aria-pressed={isSelected}
                  onClick={() => setSelectedDate(key)}
                >
                  <span>{date.getDate()}</span>
                  {daysJobs.length > 0 && (
                    <span className="calendar-day-dots" aria-hidden="true">
                      {daysJobs.slice(0, 3).map((job) => (
                        <i className={`dot-${job.platform.toLowerCase()}`} key={job.id} />
                      ))}
                      {daysJobs.length > 3 && <b>+{daysJobs.length - 3}</b>}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <div className="calendar-legend">
            <span><i className="dot-x" /> X</span>
            <span><i className="dot-linkedin" /> LinkedIn</span>
            <span><i className="dot-other" /> Other</span>
          </div>
        </section>

        <aside className="calendar-agenda">
          <div className="calendar-agenda-heading">
            <div>
              <span className="calendar-section-label">DAY PLAN</span>
              <h2>{new Date(`${selectedDate}T12:00:00`).toLocaleDateString(undefined, {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}</h2>
            </div>
            <span className="calendar-agenda-count">{selectedJobs.length}</span>
          </div>
          {selectedJobs.length ? (
            <div className="calendar-agenda-list">
              {selectedJobs.map((job, index) => (
                <article className={`calendar-event-card event-${index % 3}`} key={job.id}>
                  <div className="calendar-event-time">
                    <Clock3 size={14} /> {formatTime(job.scheduled_at)}
                  </div>
                  <div className="calendar-event-main">
                    <span className={`calendar-platform-chip ${job.platform.toLowerCase()}`}>
                      {job.platform}
                    </span>
                    <h3>{job.platform === "x" ? "X post" : `${job.platform} post`}</h3>
                    <p>Draft #{job.draft_id}</p>
                  </div>
                  <div className="calendar-event-footer">
                    <span className={`calendar-status ${job.status}`}>
                      {job.status === "completed" ? <CheckCircle2 size={13} /> : <span />}
                      {job.status}
                    </span>
                    {job.status === "pending" && (
                      <button
                        type="button"
                        className="calendar-cancel-button"
                        onClick={() => void handleCancel(job.id)}
                        disabled={cancellingId === job.id}
                      >
                        {cancellingId === job.id ? (
                          <span className="spinner" />
                        ) : (
                          <><XCircle size={14} /> Cancel</>
                        )}
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="calendar-day-empty">
              <div><CalendarDays size={20} /></div>
              <strong>A little breathing room.</strong>
              <span>Nothing is scheduled for this day.</span>
              <p>Approve and schedule a draft from Content to add it to your rhythm.</p>
            </div>
          )}
        </aside>
      </div>

      {jobs.length === 0 && (
        <div className="calendar-first-step">
          <span className="calendar-first-step-icon"><Sparkles size={16} /></span>
          <span><strong>Your calendar is clear.</strong> When you schedule a post, you’ll find it here.</span>
        </div>
      )}
    </div>
  );
}
