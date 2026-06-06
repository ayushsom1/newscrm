import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Proposal, ProposalStatus } from "@/types/proposal";
import { dateOnly } from "@/lib/format";
import { showSuccess } from "@/lib/toast";
import { useAuth } from "@/lib/auth";

const STATUS_STYLES: Record<ProposalStatus, string> = {
  DRAFT: "bg-zinc-100 text-ink/80 border-zinc-200",
  APPROVED: "bg-amber-50 text-amber-800 border-amber-200",
  SENT: "bg-green-50 text-green-800 border-green-200",
  REJECTED: "bg-red-50 text-brand border-red-200",
};

interface Props {
  advertiserId: number;
}

export default function ProposalsPanel({ advertiserId }: Props) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const canWrite = user?.role === "ADMIN" || user?.role === "SALES";
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [edit, setEdit] = useState<{ subject: string; body: string } | null>(
    null,
  );

  const { data, isLoading, isError } = useQuery<Proposal[]>({
    queryKey: ["proposals", advertiserId],
    queryFn: async () =>
      (await api.get<Proposal[]>(`/advertisers/${advertiserId}/proposals`)).data,
  });

  const draft = useMutation({
    mutationFn: async () =>
      (
        await api.post<Proposal>(
          `/advertisers/${advertiserId}/proposals/draft`,
        )
      ).data,
    onSuccess: async (p) => {
      await qc.invalidateQueries({ queryKey: ["proposals", advertiserId] });
      setExpandedId(p.id);
    },
  });

  const transition = useMutation({
    mutationFn: async ({ id, action }: { id: number; action: string }) =>
      (await api.post<Proposal>(`/proposals/${id}/${action}`)).data,
    onSuccess: async (_d, { action }) => {
      await qc.invalidateQueries({ queryKey: ["proposals", advertiserId] });
      const map: Record<string, string> = {
        approve: "Proposal approved",
        reject: "Proposal rejected",
        send: "Proposal sent",
      };
      showSuccess(map[action] ?? "Done");
    },
  });

  const savePatch = useMutation({
    mutationFn: async ({
      id,
      patch,
    }: {
      id: number;
      patch: { subject: string; body: string };
    }) => (await api.patch<Proposal>(`/proposals/${id}`, patch)).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["proposals", advertiserId] });
      setEdit(null);
      showSuccess("Edits saved");
    },
  });

  return (
    <div className="bg-white border border-zinc-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-ink">
          Proposals ({data?.length ?? 0})
        </div>
        {canWrite && (
          <button
            disabled={draft.isPending}
            onClick={() => draft.mutate()}
            className="bg-ai text-white text-sm px-3 py-1.5 rounded hover:bg-ai/90 disabled:opacity-60"
          >
            {draft.isPending ? "Drafting…" : "Draft with AI"}
          </button>
        )}
      </div>

      {isLoading && <p className="text-sm text-ink/60 mt-3">Loading…</p>}
      {isError && <p className="text-sm text-brand mt-3">Failed to load.</p>}
      {draft.isError && (
        <p className="text-sm text-brand mt-3">AI draft failed — try again.</p>
      )}

      {data?.length === 0 && (
        <p className="text-sm text-ink/60 mt-3">
          No proposals yet. Click "Draft with AI" — Claude/GPT writes a starting
          point; a human approves before send.
        </p>
      )}

      <ul className="mt-3 divide-y divide-zinc-100">
        {data?.map((p) => {
          const open = expandedId === p.id;
          const editing = edit && open;
          return (
            <li key={p.id} className="py-3">
              <button
                onClick={() => setExpandedId(open ? null : p.id)}
                className="w-full text-left flex items-start gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-ink truncate">
                      {p.subject}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded border ${STATUS_STYLES[p.status]}`}
                    >
                      {p.status}
                    </span>
                    {p.source === "AI_DRAFT" && (
                      <span className="text-xs px-2 py-0.5 rounded border border-ai/30 text-ai bg-blue-50">
                        AI draft
                      </span>
                    )}
                    {p.needs_human && p.status === "DRAFT" && (
                      <span className="text-xs px-2 py-0.5 rounded border border-amber-200 text-amber-800 bg-amber-50">
                        Needs human
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-ink/50 mt-0.5">
                    {dateOnly(p.created_at)}
                    {p.model_used && ` · ${p.model_used}`}
                  </div>
                </div>
                <span className="text-ink/40 text-xs">{open ? "▲" : "▼"}</span>
              </button>

              {open && (
                <div className="mt-3 space-y-3">
                  {p.needs_human && p.status === "DRAFT" && (
                    <div className="text-xs bg-amber-50 border border-amber-200 text-amber-800 rounded p-2">
                      {p.needs_human_reason ??
                        "Flagged for human review before approval."}
                    </div>
                  )}

                  {editing ? (
                    <div className="space-y-2">
                      <input
                        className={inputCls}
                        value={edit.subject}
                        onChange={(e) =>
                          setEdit({ ...edit, subject: e.target.value })
                        }
                      />
                      <textarea
                        rows={10}
                        className={inputCls}
                        value={edit.body}
                        onChange={(e) =>
                          setEdit({ ...edit, body: e.target.value })
                        }
                      />
                      <div className="flex gap-2">
                        <button
                          disabled={savePatch.isPending}
                          onClick={() =>
                            savePatch.mutate({ id: p.id, patch: edit })
                          }
                          className="bg-ink text-white text-sm px-3 py-1 rounded disabled:opacity-60"
                        >
                          Save edits
                        </button>
                        <button
                          onClick={() => setEdit(null)}
                          className="text-sm text-ink/70 px-2 py-1"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <pre className="whitespace-pre-wrap text-sm text-ink font-sans bg-zinc-50 border border-zinc-200 rounded p-3 max-h-96 overflow-auto">
                      {p.body}
                    </pre>
                  )}

                  {canWrite && !editing && (
                    <div className="flex flex-wrap gap-2">
                      {p.status === "DRAFT" && (
                        <>
                          <button
                            onClick={() =>
                              setEdit({ subject: p.subject, body: p.body })
                            }
                            className="text-sm border border-zinc-300 px-3 py-1 rounded hover:bg-zinc-50"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => {
                              const msg = p.needs_human
                                ? "This draft is flagged for human review. Approve anyway?"
                                : "Approve this draft?";
                              if (confirm(msg))
                                transition.mutate({
                                  id: p.id,
                                  action: "approve",
                                });
                            }}
                            className="bg-ink text-white text-sm px-3 py-1 rounded hover:bg-ink/90"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => {
                              if (confirm("Reject this draft?"))
                                transition.mutate({
                                  id: p.id,
                                  action: "reject",
                                });
                            }}
                            className="text-sm text-brand border border-red-200 px-3 py-1 rounded hover:bg-red-50"
                          >
                            Reject
                          </button>
                        </>
                      )}
                      {p.status === "APPROVED" && (
                        <button
                          onClick={() => {
                            if (confirm("Send this proposal now?"))
                              transition.mutate({
                                id: p.id,
                                action: "send",
                              });
                          }}
                          className="bg-green-700 text-white text-sm px-3 py-1 rounded hover:bg-green-800"
                        >
                          Send
                        </button>
                      )}
                      {p.status === "SENT" && (
                        <span className="text-xs text-ink/60">
                          Sent {dateOnly(p.sent_at)}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

const inputCls =
  "w-full border border-zinc-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40";
