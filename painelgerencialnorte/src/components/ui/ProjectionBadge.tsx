type ProjectionBadgeProps = {
  label: string;
  tone?: "green" | "blue" | "orange" | "red" | "muted";
};

const toneClass = {
  green: "bg-[#e7f6ee] text-[#176a45]",
  blue: "bg-[#eaf4ff] text-[#1c5d8f]",
  orange: "bg-[#fff7e6] text-[#9a5a00]",
  red: "bg-[#fff1f1] text-[#9b1c1c]",
  muted: "bg-muted text-[#60786c]",
};

export function ProjectionBadge({ label, tone = "muted" }: ProjectionBadgeProps) {
  return <span className={`inline-flex rounded-md px-2.5 py-1 text-xs font-semibold ${toneClass[tone]}`}>{label}</span>;
}

