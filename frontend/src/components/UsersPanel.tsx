import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { UserDetail } from "@/types/settings";
import { ROLES } from "@/types/settings";
import { dateOnly } from "@/lib/format";
import { showSuccess } from "@/lib/toast";

const createSchema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
  role: z.enum(ROLES),
  password: z.string().min(8, "min 8 chars"),
});
type CreateVals = z.infer<typeof createSchema>;

export default function UsersPanel() {
  const qc = useQueryClient();
  const { user: me } = useAuth();
  const [showCreate, setShowCreate] = useState(false);
  const [resetFor, setResetFor] = useState<UserDetail | null>(null);

  const usersQ = useQuery<UserDetail[]>({
    queryKey: ["users"],
    queryFn: async () => (await api.get<UserDetail[]>("/users")).data,
  });

  const createForm = useForm<CreateVals>({
    resolver: zodResolver(createSchema),
    defaultValues: { role: "SALES" },
  });

  const create = useMutation({
    mutationFn: async (vals: CreateVals) =>
      (await api.post<UserDetail>("/users", vals)).data,
    onSuccess: async (u) => {
      await qc.invalidateQueries({ queryKey: ["users"] });
      createForm.reset();
      setShowCreate(false);
      showSuccess(`Created ${u.email}`);
    },
  });

  const updateRole = useMutation({
    mutationFn: async ({ id, role }: { id: number; role: string }) =>
      (await api.patch<UserDetail>(`/users/${id}`, { role })).data,
    onSuccess: async (u) => {
      await qc.invalidateQueries({ queryKey: ["users"] });
      showSuccess(`Role updated to ${u.role}`);
    },
  });

  const toggleActive = useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) =>
      (await api.patch<UserDetail>(`/users/${id}`, { is_active })).data,
    onSuccess: async (u) => {
      await qc.invalidateQueries({ queryKey: ["users"] });
      showSuccess(u.is_active ? "User activated" : "User deactivated");
    },
  });

  const remove = useMutation({
    mutationFn: async (id: number) => await api.delete(`/users/${id}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["users"] });
      showSuccess("User deleted");
    },
  });

  const isAdmin = me?.role === "ADMIN";

  return (
    <div className="space-y-4">
      {isAdmin && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowCreate((v) => !v)}
            className="text-sm border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50"
          >
            {showCreate ? "Cancel" : "+ New user"}
          </button>
        </div>
      )}

      {showCreate && isAdmin && (
        <form
          onSubmit={createForm.handleSubmit((v) => create.mutate(v))}
          className="bg-white border border-zinc-200 rounded-lg p-4 grid grid-cols-1 md:grid-cols-5 gap-3 items-end"
        >
          <Field label="Name" error={createForm.formState.errors.name?.message}>
            <input {...createForm.register("name")} className={input} />
          </Field>
          <Field label="Email" error={createForm.formState.errors.email?.message}>
            <input type="email" {...createForm.register("email")} className={input} />
          </Field>
          <Field label="Role">
            <select {...createForm.register("role")} className={input}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Password" error={createForm.formState.errors.password?.message}>
            <input
              type="password"
              {...createForm.register("password")}
              className={input}
            />
          </Field>
          <button
            disabled={create.isPending}
            className="bg-nav text-white text-sm py-1.5 rounded hover:bg-nav-darker disabled:opacity-60"
          >
            {create.isPending ? "Saving…" : "Create"}
          </button>
          {create.isError && (
            <p className="md:col-span-5 text-xs text-brand">
              Could not create. Email might already exist.
            </p>
          )}
        </form>
      )}

      <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-ink/60 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Name</th>
              <th className="text-left px-4 py-2 font-medium">Email</th>
              <th className="text-left px-4 py-2 font-medium">Role</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
              <th className="text-left px-4 py-2 font-medium">Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {usersQ.isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-ink/50">
                  Loading…
                </td>
              </tr>
            )}
            {usersQ.data?.map((u) => {
              const isSelf = u.id === me?.id;
              return (
                <tr key={u.id} className="border-t border-zinc-100">
                  <td className="px-4 py-2 text-ink">
                    {u.name}
                    {isSelf && (
                      <span className="ml-2 text-[10px] uppercase text-ink/40">
                        you
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-ink/70">{u.email}</td>
                  <td className="px-4 py-2">
                    {isAdmin && !isSelf ? (
                      <select
                        value={u.role}
                        onChange={(e) =>
                          updateRole.mutate({ id: u.id, role: e.target.value })
                        }
                        className="border border-zinc-300 rounded px-2 py-1 text-xs"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-ink/70">{u.role}</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {isAdmin && !isSelf ? (
                      <button
                        onClick={() =>
                          toggleActive.mutate({
                            id: u.id,
                            is_active: !u.is_active,
                          })
                        }
                        className={`text-xs px-2 py-0.5 rounded border ${
                          u.is_active
                            ? "border-green-200 bg-green-50 text-green-800"
                            : "border-zinc-300 bg-zinc-100 text-ink/60"
                        }`}
                      >
                        {u.is_active ? "Active" : "Inactive"}
                      </button>
                    ) : (
                      <span
                        className={`text-xs ${u.is_active ? "text-green-700" : "text-ink/50"}`}
                      >
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-ink/70">{dateOnly(u.created_at)}</td>
                  <td className="px-4 py-2 text-right space-x-3">
                    {isAdmin && (
                      <button
                        onClick={() => setResetFor(u)}
                        className="text-xs text-ai hover:underline"
                      >
                        Reset password
                      </button>
                    )}
                    {isAdmin && !isSelf && (
                      <button
                        onClick={() => {
                          if (confirm(`Delete ${u.email}?`))
                            remove.mutate(u.id);
                        }}
                        className="text-xs text-brand hover:underline"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {resetFor && <ResetPasswordModal user={resetFor} onClose={() => setResetFor(null)} />}
    </div>
  );
}

function ResetPasswordModal({
  user,
  onClose,
}: {
  user: UserDetail;
  onClose: () => void;
}) {
  const [pw, setPw] = useState("");
  const reset = useMutation({
    mutationFn: async () =>
      await api.post(`/users/${user.id}/reset-password`, { new_password: pw }),
    onSuccess: () => {
      showSuccess(`Password reset for ${user.email}`);
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-nav/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-sm space-y-3">
        <div className="text-sm font-medium text-ink">
          Reset password for {user.email}
        </div>
        <input
          type="password"
          autoFocus
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          placeholder="New password (min 8 chars)"
          className="w-full border border-zinc-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40"
        />
        {reset.isError && (
          <p className="text-xs text-brand">Failed to reset.</p>
        )}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="text-sm text-ink/70 px-3 py-1.5"
          >
            Cancel
          </button>
          <button
            disabled={pw.length < 8 || reset.isPending}
            onClick={() => reset.mutate()}
            className="bg-nav text-white text-sm px-3 py-1.5 rounded disabled:opacity-60"
          >
            {reset.isPending ? "Saving…" : "Reset"}
          </button>
        </div>
      </div>
    </div>
  );
}

const input =
  "w-full border border-zinc-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40";

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-ink/70">{label}</label>
      {children}
      {error && <p className="text-xs text-brand">{error}</p>}
    </div>
  );
}
