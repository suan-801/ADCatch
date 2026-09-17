import type { AdStatus } from "@/lib/types";

const LABEL: Record<AdStatus, string> = {
  NEW: "New",
  ACTIVE: "Active",
  INACTIVE: "Inactive",
};

// 색상은 PRD.MD 5.1 / .cursorrules 의 Status Badge 스펙 그대로.
const STYLE: Record<AdStatus, string> = {
  NEW: "bg-blue-50 text-status-new border border-status-new/30",
  ACTIVE: "bg-green-50 text-status-active border border-status-active/30",
  INACTIVE: "bg-slate-100 text-status-inactive border border-status-inactive/30",
};

export function StatusBadge({ status }: { status: AdStatus }) {
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${STYLE[status]}`}>
      {LABEL[status]}
    </span>
  );
}
