interface Props {
  title: string;
  sprint: string;
}

export default function Placeholder({ title, sprint }: Props) {
  return (
    <div className="space-y-2">
      <h1 className="text-xl font-semibold text-ink">{title}</h1>
      <p className="text-sm text-ink/60">Lands in {sprint}.</p>
    </div>
  );
}
