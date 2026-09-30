import { CalendarDays, Loader2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { cancelScheduledJob, getScheduledJobs } from "../lib/api";
import type { ScheduledJob } from "../types";

export function CalendarWorkspace() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await getScheduledJobs();
      setJobs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleCancel = async (id: number) => {
    try {
      await cancelScheduledJob(id);
      await fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-gray-500">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 text-gray-900 flex flex-col items-center">
      <div className="w-full max-w-4xl p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-xl shadow-sm">
            <CalendarDays className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Content Calendar
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              Review and manage your scheduled content
            </p>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div className="p-12 text-center bg-white border border-gray-100 rounded-2xl shadow-sm">
            <CalendarDays className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">No scheduled content.</p>
            <p className="text-gray-400 text-sm mt-2">
              Approve and schedule drafts from the Content workspace.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row gap-6 hover:border-blue-200 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="px-3 py-1 bg-blue-50 text-blue-700 text-xs font-semibold uppercase tracking-wider rounded-full border border-blue-100">
                      {job.platform}
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        job.status === "pending"
                          ? "text-yellow-600"
                          : job.status === "completed"
                          ? "text-green-600"
                          : job.status === "failed"
                          ? "text-red-600"
                          : "text-gray-500"
                      }`}
                    >
                      {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                    </span>
                  </div>
                  <div className="text-gray-800 text-lg font-medium">
                    Scheduled for: {new Date(job.scheduled_at).toLocaleString()}
                  </div>
                  <div className="text-sm text-gray-500 mt-2">
                    Draft ID: {job.draft_id}
                  </div>
                </div>

                {job.status === "pending" && (
                  <div className="flex items-center">
                    <button
                      onClick={() => handleCancel(job.id)}
                      className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors font-medium border border-transparent hover:border-red-100"
                    >
                      <XCircle className="w-5 h-5" /> Cancel
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
