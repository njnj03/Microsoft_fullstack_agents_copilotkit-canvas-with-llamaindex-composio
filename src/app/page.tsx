// /src/app/page.tsx
"use client";

import { useRef, useState } from "react";
import { CopilotKit, useCopilotAction } from "@copilotkit/react-core";

type Task = {
  id: string;
  title: string;
  owner?: string;
  due?: string;
  status?: "todo" | "doing" | "done";
};

type Toast = { id: string; kind: "success" | "error" | "info"; msg: string };

export default function Page() {
  const runtimeUrl =
    process.env.NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL || "http://localhost:9000";

  // unified state (logic unchanged)
  const [channel, setChannel] = useState("#general");
  const [input, setInput] = useState("");
  const [docId, setDocId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function toast(kind: Toast["kind"], msg: string) {
    const id = crypto.randomUUID();
    setToasts((t) => [...t, { id, kind, msg }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3000);
  }

  // ===== actions (logic unchanged) =====
  useCopilotAction({
    name: "addTask",
    description: "Add a task (title, owner, due, status) to the table",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "owner", type: "string" },
      { name: "due", type: "string" },
      { name: "status", type: "string", enum: ["todo", "doing", "done"] },
    ],
    handler: async (p: { title: string; owner?: string; due?: string; status?: Task["status"] }) => {
      const t: Task = {
        id: crypto.randomUUID(),
        title: p.title,
        owner: p.owner,
        due: p.due,
        status: p.status ?? "todo",
      };
      setTasks((xs) => [...xs, t]);
      return { ok: true, id: t.id };
    },
  });

  useCopilotAction({
    name: "updateTask",
    description: "Update a task by id",
    parameters: [
      { name: "id", type: "string", required: true },
      { name: "title", type: "string" },
      { name: "owner", type: "string" },
      { name: "due", type: "string" },
      { name: "status", type: "string", enum: ["todo", "doing", "done"] },
    ],
    handler: async (p: { id: string; title?: string; owner?: string; due?: string; status?: Task["status"] }) => {
      setTasks((xs) => xs.map((x) => (x.id === p.id ? { ...x, ...p } : x)));
      return { ok: true };
    },
  });

  useCopilotAction({
    name: "extractTasksFromDoc",
    description:
      "Use LlamaIndex to extract tasks from the uploaded minutes (doc_id required)",
    parameters: [{ name: "doc_id", type: "string", required: true }],
    handler: async ({ doc_id }: { doc_id: string }) => {
      const res = await fetch("/api/copilotkit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: "/extract-tasks", payload: { doc_id } }),
      });
      const data = await res.json();
      if (Array.isArray(data.tasks)) {
        const mapped: Task[] = data.tasks.map((t: { title: string; owner?: string; due?: string; status?: Task["status"] }) => ({
          id: crypto.randomUUID(),
          title: t.title,
          owner: t.owner,
          due: t.due,
          status: t.status ?? "todo",
        }));
        setTasks(mapped);
        toast("success", `Extracted ${mapped.length} task(s)`);
      } else {
        toast("error", "No tasks returned");
      }
      return data;
    },
  });

  useCopilotAction({
    name: "sendPromptToSlack",
    description: "Send a freeform prompt to Slack via the bot",
    parameters: [
      { name: "channel", type: "string" },
      { name: "prompt", type: "string", required: true },
    ],
    handler: async ({ channel: ch, prompt: pr }: { channel?: string; prompt: string }) => {
      const res = await fetch("/api/copilotkit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: "/compose-to-slack",
          payload: { channel: ch || channel, prompt: pr },
        }),
      });
      const ok = res.ok;
      if (ok) {
        toast("success", "Sent to Slack");
      } else {
        toast("error", "Slack failed");
      }
      const data = await res.json().catch(() => ({} as Record<string, unknown>));
      return { ok, ...data };
    },
  });

  useCopilotAction({
    name: "pushTasksToSlack",
    description: "Post the current task table to Slack",
    parameters: [{ name: "channel", type: "string" }],
    handler: async ({ channel: ch }: { channel?: string }) => {
      const res = await fetch("/api/copilotkit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: "/push-slack",
          payload: { channel: ch || channel, tasks },
        }),
      });
      const ok = res.ok;
      if (ok) {
        toast("success", "Tasks posted");
      } else {
        toast("error", "Post failed");
      }
      const data = await res.json().catch(() => ({} as Record<string, unknown>));
      return { ok, ...data };
    },
  });

  // ===== helpers (logic unchanged) =====
  async function uploadFile(file: File) {
    const MAX_BYTES = 10 * 1024 * 1024; // 10MB
    if (file.size > MAX_BYTES) {
      toast("error", "File too large (max 10MB)");
      return { ok: false };
    }

    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/copilotkit?path=/ingest", {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        // try to extract JSON error, otherwise use text/status
        const txt = await res.text().catch(() => "");
        let msg = txt || res.statusText || `status ${res.status}`;
        try {
          const parsed = JSON.parse(txt);
          if (parsed && typeof parsed === "object" && "error" in parsed) {
            const maybe = parsed as Record<string, unknown>;
            const e = maybe.error ?? maybe.message;
            if (e !== undefined) msg = String(e);
          }
        } catch {
          // not JSON
        }
        toast("error", `Upload failed: ${msg}`);
        return { ok: false };
      }

      const data = (await res.json().catch(() => null)) as
        | Record<string, unknown>
        | null;

      if (data && typeof data === "object" && "doc_id" in data) {
        const obj = data as Record<string, unknown>;
        const doc = obj.doc_id;
        setDocId(String(doc));
        toast("success", "Minutes attached");
        return { ok: true, doc_id: doc };
      } else {
        const message = data && typeof data === "object" && (data.message || data.error)
          ? String((data.message ?? data.error) as string)
          : "Upload failed";
        toast("error", message);
        return { ok: false };
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      toast("error", `Upload failed: ${message}`);
      return { ok: false };
    } finally {
      setUploading(false);
    }
  }

  async function submitUnified() {
    if (!input.trim() && !docId) return;
    setBusy(true);

    const guidance =
      `You are a unified copilot for meeting minutes and Slack.\n` +
      `- If minutes are attached (doc_id present) and the user asks to extract/summarize action items, call extractTasksFromDoc with that doc_id, then addTask/updateTask as needed.\n` +
      `- If the user asks to message or announce on Slack, call sendPromptToSlack or pushTasksToSlack (use channel: ${channel}).\n` +
      `Return concise updates. Keep tasks atomic: {title, owner, due, status}.`;

    const text =
      (docId ? `(context: doc_id=${docId}) ` : "") + input.trim();

    window.dispatchEvent(
      new CustomEvent("copilotkit:user-intent", {
        detail: { text: `${guidance}\n\nUser: ${text}` },
      })
    );

    setBusy(false);
    setInput("");
  }

  function removeTask(id: string) {
    setTasks((xs) => xs.filter((t) => t.id !== id));
  }

  // ===== UI with sage + cream theme =====
  return (
    <CopilotKit runtimeUrl={runtimeUrl}>
      <div className="min-h-screen bg-[#FDFBF7]">
        {/* toasts */}
        <div className="fixed top-4 right-4 z-50 space-y-2">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={`rounded-lg px-3 py-2 text-sm shadow-lg ${
                t.kind === "success"
                  ? "bg-[#9BBF9B] text-white"
                  : t.kind === "error"
                  ? "bg-[#C0605E] text-white"
                  : "bg-[#6B7B6E] text-white"
              }`}
            >
              {t.msg}
            </div>
          ))}
        </div>

        <main className="mx-auto max-w-6xl p-6 space-y-6">
          {/* header */}
          <div className="rounded-2xl border border-[#C9D6C5] bg-gradient-to-br from-[#E6EAE3] via-[#F3F2EC] to-[#FDFBF7] p-5">
            <h1 className="text-2xl font-semibold text-[#2F3E2E]">
              Minutes → Tasks → Slack
            </h1>
            <p className="mt-1 text-sm text-[#3F4F3F]">
              One prompt for everything. Attach minutes or type a command. The copilot
              decides between analysis (LlamaIndex) and Slack (Composio).
            </p>
          </div>

          {/* unified prompt */}
          <section className="rounded-2xl border border-[#C9D6C5] bg-[#FEFEFA] p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <button
                className="rounded-xl border border-[#C9D6C5] bg-[#F3F2EC] px-3 py-2 text-sm text-[#2F3E2E] hover:bg-[#E6EAE3]"
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? "Uploading…" : docId ? "Replace minutes" : "Attach minutes"}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md,.pdf,.doc,.docx,.rtf"
                className="hidden"
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    const result = await uploadFile(f);
                    // helpful client-side debug to inspect what happened
                    // visible in browser console
                    console.debug("uploadFile result:", result);
                  }
                }}
              />

              <input
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                className="w-48 rounded-xl border border-[#C9D6C5] bg-white px-3 py-2 text-sm text-[#2F3E2E] placeholder:text-[#6B7B6E]"
                placeholder="#general"
              />

              <div className="ml-auto text-xs text-[#6B7B6E]">
                Tip: “Extract action items and announce in {channel}”
              </div>
            </div>

            <div className="mt-3 flex items-end gap-2">
              <textarea
                className="h-20 flex-1 resize-none rounded-xl border border-[#C9D6C5] bg-white px-3 py-2 text-sm text-[#2F3E2E] placeholder:text-[#6B7B6E] focus:outline-none focus:ring-2 focus:ring-[#C9D6C5]"
                placeholder={
                  docId
                    ? "e.g., Extract action items from attached minutes and post to Slack"
                    : "e.g., Ask the bot to summarize blockers in #general"
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submitUnified();
                  }
                }}
              />
              <button
                onClick={submitUnified}
                disabled={busy || (!input.trim() && !docId)}
className="rounded-xl border border-[#9BBF9B] bg-[#9BBF9B] px-4 py-2 text-sm font-bold text-[#1F2D1F] hover:bg-[#87A886] disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </section>

          {/* tasks */}
          <section className="rounded-2xl border border-[#C9D6C5] bg-[#FEFEFA] shadow-sm">
            <div className="flex items-center justify-between px-4 pt-4">
              <h2 className="text-sm font-semibold text-[#2F3E2E]">Extracted tasks</h2>
              <p className="text-xs text-[#6B7B6E]">
                Edit before posting to Slack. Keep tasks atomic.
              </p>
            </div>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-[#E6EAE3] text-[#2F3E2E]">
                  <tr>
                    <th className="p-2 text-left font-medium">Title</th>
                    <th className="p-2 text-left font-medium">Owner</th>
                    <th className="p-2 text-left font-medium">Due</th>
                    <th className="p-2 text-left font-medium">Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.length === 0 ? (
                    <tr>
                      <td
                        className="p-6 text-center text-[#6B7B6E]"
                        colSpan={5}
                      >
                        No tasks yet — attach minutes and ask “extract action items”.
                      </td>
                    </tr>
                  ) : (
                    tasks.map((t) => (
                      <tr key={t.id} className="border-t border-[#E6EAE3]">
                        <td className="p-2">
                          <input
                            className="w-full rounded-lg border border-[#C9D6C5] bg-white px-2 py-1 text-[#2F3E2E]"
                            value={t.title}
                            onChange={(e) =>
                              setTasks((xs) =>
                                xs.map((x) =>
                                  x.id === t.id ? { ...x, title: e.target.value } : x
                                )
                              )
                            }
                          />
                        </td>
                        <td className="p-2">
                          <input
                            className="w-full rounded-lg border border-[#C9D6C5] bg-white px-2 py-1 text-[#2F3E2E]"
                            value={t.owner ?? ""}
                            onChange={(e) =>
                              setTasks((xs) =>
                                xs.map((x) =>
                                  x.id === t.id ? { ...x, owner: e.target.value } : x
                                )
                              )
                            }
                            placeholder="owner"
                          />
                        </td>
                        <td className="p-2">
                          <input
                            className="w-full rounded-lg border border-[#C9D6C5] bg-white px-2 py-1 text-[#2F3E2E]"
                            value={t.due ?? ""}
                            onChange={(e) =>
                              setTasks((xs) =>
                                xs.map((x) =>
                                  x.id === t.id ? { ...x, due: e.target.value } : x
                                )
                              )
                            }
                            placeholder="e.g. Fri or 2025-10-01"
                          />
                        </td>
                        <td className="p-2">
                          <select
                            className="w-full rounded-lg border border-[#C9D6C5] bg-white px-2 py-1 text-[#2F3E2E]"
                            value={t.status ?? "todo"}
                            onChange={(e) =>
                              setTasks((xs) =>
                                xs.map((x) =>
                                  x.id === t.id
                                    ? { ...x, status: e.target.value as Task["status"] }
                                    : x
                                )
                              )
                            }
                          >
                            <option value="todo">todo</option>
                            <option value="doing">doing</option>
                            <option value="done">done</option>
                          </select>
                        </td>
                        <td className="p-2 text-right">
                          <button
                            className="rounded-lg border border-[#C9D6C5] px-2 py-1 text-xs text-[#A33E3E] hover:bg-[#F3F2EC]"
                            onClick={() => removeTask(t.id)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex justify-end border-t border-[#E6EAE3] bg-[#F3F2EC] px-4 py-3">
              <button
                onClick={() =>
                  window.dispatchEvent(
                    new CustomEvent("copilotkit:user-intent", {
                      detail: {
                        text: `Post all current tasks to Slack channel ${channel}.`,
                      },
                    })
                  )
                }
                disabled={tasks.length === 0}
                className="rounded-xl border border-[#9BBF9B] bg-[#9BBF9B] px-3 py-2 text-sm text-white hover:bg-[#87A886] disabled:opacity-50"
              >
                Post tasks to {channel}
              </button>
            </div>
          </section>
        </main>
      </div>
    </CopilotKit>
  );
}

/* no inline icon helpers needed */
