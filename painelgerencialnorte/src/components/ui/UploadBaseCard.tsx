type UploadBaseCardProps = {
  title: string;
  description: string;
};

export function UploadBaseCard({ title, description }: UploadBaseCardProps) {
  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h3 className="font-semibold text-foreground">{title}</h3>
      <p className="mt-1 text-sm text-[#60786c]">{description}</p>
      <div className="mt-4">
        <input className="focus-ring block w-full rounded-md border border-dashed border-border bg-muted px-3 py-3 text-sm" type="file" />
      </div>
    </section>
  );
}

