export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="max-w-3xl">
      {eyebrow && (
        <p className="mb-2 text-[13px] font-medium tracking-[0.01em] text-text-tertiary">
          {eyebrow}
        </p>
      )}
      <h1 className="font-display text-[28px] leading-[1.15] font-semibold tracking-[-0.022em] text-balance text-text sm:text-[34px]">
        {title}
      </h1>
      {description && (
        <p className="mt-3 text-[15px] leading-6 text-pretty text-text-secondary sm:text-[17px] sm:leading-[26px]">
          {description}
        </p>
      )}
      {children}
    </header>
  );
}
