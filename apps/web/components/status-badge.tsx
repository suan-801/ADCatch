import type { AdStatus } from "@/lib/types";

const LABEL: Record<AdStatus, string> = {
  NEW: "New",
  ACTIVE: "Active",
  INACTIVE: "Inactive",
};

// 상태 색상(파랑/초록/회색)은 기능 의미 유지를 위해 기존 값을 그대로 보존.
const STYLE: Record<AdStatus, string> = {
  NEW: "bg-blue-50 text-status-new border border-status-new/30",
  ACTIVE: "bg-green-50 text-status-active border border-status-active/30",
  INACTIVE: "bg-slate-100 text-status-inactive border border-status-inactive/30",
};

export function StatusBadge({ status }: { status: AdStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${STYLE[status]}`}>
      {LABEL[status]}
    </span>
  );
}
