import type { Competitor } from "@/lib/types";

export function CompetitorFilter({
  competitors,
  selectedId,
  onSelect,
}: {
  competitors: Competitor[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 overflow-x-auto pb-1">
      <button
        onClick={() => onSelect(null)}
        className={`shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
          selectedId === null
            ? "border-brand bg-brand text-white"
            : "border-border text-muted hover:border-brand/40 hover:text-foreground"
        }`}
      >
        전체
      </button>
      {competitors.map((c) => (
        <button
          key={c.id}
          onClick={() => onSelect(c.id)}
          className={`shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
            selectedId === c.id
              ? "border-brand bg-brand text-white"
              : "border-border text-muted hover:border-brand/40 hover:text-foreground"
          }`}
        >
          {c.name}
        </button>
      ))}
    </div>
  );
}
