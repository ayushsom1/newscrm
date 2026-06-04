import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Health = { status: string };

export default function App() {
  const { data, isLoading, isError } = useQuery<Health>({
    queryKey: ["health"],
    queryFn: async () => (await api.get("/health")).data,
  });

  return (
    <div className="min-h-screen flex items-center justify-center font-sans">
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-semibold text-ink">News CRM</h1>
        <p className="text-sm text-ink/60">Sprint 0 — scaffolding</p>
        <div className="text-sm">
          API status:&nbsp;
          {isLoading && <span className="text-ink/60">checking…</span>}
          {isError && <span className="text-brand">unreachable</span>}
          {data && <span className="text-green-700">{data.status}</span>}
        </div>
      </div>
    </div>
  );
}
