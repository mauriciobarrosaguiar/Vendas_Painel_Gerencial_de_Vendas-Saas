type ExportButtonProps = {
  label: string;
};

export function ExportButton({ label }: ExportButtonProps) {
  return (
    <button className="focus-ring rounded-md border border-border bg-surface px-4 py-2 text-sm font-semibold text-primary hover:bg-muted">
      {label}
    </button>
  );
}

