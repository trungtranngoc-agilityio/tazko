import { useId, type ReactNode } from "react";
import { Icon, type IconName } from "@/shared/ui/Icon";

/** A titled group of board tiles (prototype .sechd), named by its heading. */
export function Section({
  icon,
  title,
  children,
}: {
  icon: IconName;
  title: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="mb-6">
      <h2 id={id} className="mb-2.5 flex items-center gap-2 font-bold">
        <span className="text-muted">
          <Icon name={icon} />
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}

export function Grid({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-3.5">{children}</div>
  );
}
