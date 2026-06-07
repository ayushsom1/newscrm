import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

const schema = z.object({
  email: z.string().email("enter a valid email"),
  password: z.string().min(1, "required"),
});

type FormVals = z.infer<typeof schema>;

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormVals>({ resolver: zodResolver(schema) });

  const onSubmit = async (vals: FormVals) => {
    setServerError(null);
    try {
      await login(vals.email, vals.password);
      nav("/");
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "login failed";
      setServerError(msg);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 font-sans p-4">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full max-w-sm bg-white border border-zinc-200 rounded-lg p-6 sm:p-8 space-y-5 shadow-sm"
      >
        <div>
          <h1 className="text-2xl font-semibold text-ink">News CRM</h1>
          <p className="text-sm text-ink/60">Sign in to continue</p>
        </div>

        <div className="space-y-1">
          <label htmlFor="email" className="text-sm font-medium text-ink">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40"
            {...register("email")}
          />
          {errors.email && <p className="text-xs text-brand">{errors.email.message}</p>}
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium text-ink">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40"
            {...register("password")}
          />
          {errors.password && <p className="text-xs text-brand">{errors.password.message}</p>}
        </div>

        {serverError && <p className="text-sm text-brand">{serverError}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-nav text-white text-sm font-medium rounded py-2 hover:bg-nav-darker disabled:opacity-60"
        >
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>

        <p className="text-xs text-ink/50">
          Dev: <code>admin@example.com</code> / <code>admin123</code>
        </p>
      </form>
    </div>
  );
}
