interface BrandProps {
  variant?: "sidebar" | "login" | "mobile";
}

export function Brand({ variant = "sidebar" }: BrandProps) {
  return (
    <span className={`canta-brand canta-brand-${variant}`}>
      <img className="canta-brand-mark" src="/canta-mark.svg" alt="" />
      <span className="canta-brand-copy">
        <strong>Canta</strong>
        <span>Social Copilot</span>
      </span>
    </span>
  );
}
