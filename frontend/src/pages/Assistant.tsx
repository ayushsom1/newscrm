import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  ChatResponse,
  Conversation,
  ConversationDetail,
  ProposedAction,
} from "@/types/assistant";

export default function Assistant() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);

  const convosQuery = useQuery<Conversation[]>({
    queryKey: ["conversations"],
    queryFn: async () => (await api.get("/conversations")).data,
  });

  const detailQuery = useQuery<ConversationDetail>({
    queryKey: ["conversation", activeId],
    queryFn: async () =>
      (await api.get<ConversationDetail>(`/conversations/${activeId}`)).data,
    enabled: !!activeId,
  });

  const actionsQuery = useQuery<ProposedAction[]>({
    queryKey: ["conversation", activeId, "actions"],
    queryFn: async () =>
      (
        await api.get<ProposedAction[]>(
          `/conversations/${activeId}/proposed-actions`,
        )
      ).data,
    enabled: !!activeId,
  });

  const send = useMutation({
    mutationFn: async (text: string) =>
      (
        await api.post<ChatResponse>("/ai/chat", {
          conversation_id: activeId ?? undefined,
          message: text,
        })
      ).data,
    onSuccess: async (resp) => {
      setActiveId(resp.conversation_id);
      await qc.invalidateQueries({ queryKey: ["conversations"] });
      await qc.invalidateQueries({
        queryKey: ["conversation", resp.conversation_id],
      });
      await qc.invalidateQueries({
        queryKey: ["conversation", resp.conversation_id, "actions"],
      });
      setInput("");
    },
  });

  const decide = useMutation({
    mutationFn: async ({
      id,
      action,
    }: {
      id: number;
      action: "approve" | "reject";
    }) =>
      (await api.post<ProposedAction>(`/proposed-actions/${id}/${action}`))
        .data,
    onSuccess: async () => {
      if (activeId) {
        await qc.invalidateQueries({
          queryKey: ["conversation", activeId, "actions"],
        });
      }
    },
  });

  const removeConvo = useMutation({
    mutationFn: async (id: number) => await api.delete(`/conversations/${id}`),
    onSuccess: async (_d, id) => {
      if (activeId === id) setActiveId(null);
      await qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  useEffect(() => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
    }
  }, [detailQuery.data?.messages?.length]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || send.isPending) return;
    send.mutate(text);
  };

  const messages = detailQuery.data?.messages ?? [];
  const pendingActions = (actionsQuery.data ?? []).filter(
    (a) => a.status === "PENDING",
  );

  return (
    <div className="grid grid-cols-[220px_1fr] gap-4 h-full">
      <aside className="bg-white border border-zinc-200 rounded-lg p-3 flex flex-col min-h-0">
        <button
          onClick={() => {
            setActiveId(null);
            setInput("");
          }}
          className="bg-ink text-white text-sm py-1.5 rounded hover:bg-ink/90"
        >
          + New chat
        </button>
        <div className="mt-3 overflow-y-auto flex-1 -mx-1">
          {convosQuery.isLoading && (
            <p className="text-xs text-ink/50 px-1">Loading…</p>
          )}
          {(convosQuery.data ?? []).map((c) => (
            <div
              key={c.id}
              className={`group flex items-center justify-between px-2 py-1.5 text-sm rounded cursor-pointer ${
                activeId === c.id ? "bg-zinc-100" : "hover:bg-zinc-50"
              }`}
              onClick={() => setActiveId(c.id)}
            >
              <span className="truncate flex-1 text-ink">{c.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm("Delete this conversation?"))
                    removeConvo.mutate(c.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-brand text-xs px-1"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="bg-white border border-zinc-200 rounded-lg flex flex-col min-h-0">
        {detailQuery.data?.model_used && (
          <header className="px-4 py-2 border-b border-zinc-200 flex items-center justify-end">
            <span className="text-[10px] uppercase tracking-wide text-ink/50 border border-zinc-200 rounded px-1.5 py-0.5">
              {detailQuery.data.model_used}
            </span>
          </header>
        )}

        <div ref={scrollerRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {activeId === null && messages.length === 0 && (
            <EmptyState />
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} />
          ))}
          {send.isPending && (
            <div className="text-xs text-ink/50 italic">Thinking…</div>
          )}
          {send.isError && (
            <div className="text-xs text-brand">
              That call failed — try again.
            </div>
          )}

          {pendingActions.length > 0 && (
            <div className="space-y-2 mt-4">
              <div className="text-xs uppercase text-ink/50">
                Pending approvals
              </div>
              {pendingActions.map((a) => (
                <ProposedActionCard
                  key={a.id}
                  action={a}
                  onApprove={() => decide.mutate({ id: a.id, action: "approve" })}
                  onReject={() => decide.mutate({ id: a.id, action: "reject" })}
                  busy={decide.isPending}
                />
              ))}
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="border-t border-zinc-200 p-3">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about the CRM, or 'draft renewals for at-risk advertisers'…"
              className="flex-1 border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40"
            />
            <button
              type="submit"
              disabled={send.isPending || !input.trim()}
              className="bg-ai text-white text-sm px-4 py-2 rounded hover:bg-ai/90 disabled:opacity-60"
            >
              {send.isPending ? "Sending…" : "Send"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-sm text-ink/60 space-y-2 max-w-lg">
      <p className="text-ink font-medium">What I can help with</p>
      <ul className="list-disc pl-5 space-y-1">
        <li>"Which advertisers are at risk of churn right now?"</li>
        <li>"Draft a renewal proposal for advertiser #3"</li>
        <li>"Who has subscriptions expiring this week?"</li>
        <li>"Summarise escalated complaints"</li>
      </ul>
      <p className="text-xs text-ink/50">
        Actions I propose are recorded for approval — I never execute on my own.
      </p>
    </div>
  );
}

function MessageBubble({
  role,
  content,
}: {
  role: "USER" | "ASSISTANT" | "SYSTEM";
  content: string;
}) {
  if (role === "SYSTEM") return null;
  const isUser = role === "USER";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-ink text-white"
            : "bg-zinc-100 text-ink border border-zinc-200"
        }`}
      >
        {content}
      </div>
    </div>
  );
}

function ProposedActionCard({
  action,
  onApprove,
  onReject,
  busy,
}: {
  action: ProposedAction;
  onApprove: () => void;
  onReject: () => void;
  busy: boolean;
}) {
  return (
    <div className="border border-ai/30 bg-blue-50/60 rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-[10px] uppercase font-medium text-ai border border-ai/30 rounded px-1.5 py-0.5">
          Proposed action
        </span>
        <span className="text-xs text-ink/60">{action.tool_name}</span>
      </div>
      <div className="text-sm text-ink">{action.summary}</div>
      <details className="text-xs text-ink/60">
        <summary className="cursor-pointer select-none">
          arguments
        </summary>
        <pre className="mt-1 whitespace-pre-wrap break-words">
          {JSON.stringify(action.arguments, null, 2)}
        </pre>
      </details>
      <div className="flex gap-2 pt-1">
        <button
          disabled={busy}
          onClick={onApprove}
          className="bg-ink text-white text-xs px-3 py-1 rounded hover:bg-ink/90 disabled:opacity-60"
        >
          Approve
        </button>
        <button
          disabled={busy}
          onClick={onReject}
          className="text-brand text-xs border border-red-200 px-3 py-1 rounded hover:bg-red-50 disabled:opacity-60"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
