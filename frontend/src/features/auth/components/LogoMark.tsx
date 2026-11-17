// The Tazko mark from the prototype: three white bars on the accent square.
export function LogoMark({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
      <rect width="44" height="44" rx="12" fill="var(--tz-accent)" />
      <rect x="10" y="10" width="7" height="24" rx="2.5" fill="#fff" />
      <rect x="19" y="10" width="7" height="15" rx="2.5" fill="#fff" opacity=".85" />
      <rect x="28" y="10" width="7" height="19" rx="2.5" fill="#fff" opacity=".7" />
    </svg>
  );
}
