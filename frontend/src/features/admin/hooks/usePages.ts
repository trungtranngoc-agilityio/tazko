import { useCallback, useEffect, useRef, useState } from "react";
import { toFailure } from "@/shared/lib/useAsync";
import type { Page } from "../api";

export type Pages<T> =
  | { kind: "loading" }
  | { kind: "failed"; code: string; status: number }
  | { kind: "ready"; items: T[]; next: number | null; more: string | null };

type Held<T> = { key: string; pages: Pages<T> };

/** Add a page after the ones shown, if the list is still the one asked for. */
function appended<T>(now: Held<T>, asked: string, page: Page<T>): Held<T> {
  if (now.key !== asked || now.pages.kind !== "ready") return now;
  const items = [...now.pages.items, ...page.items];
  return { key: asked, pages: { kind: "ready", items, next: page.next, more: null } };
}

/** Keep the list shown and remember why Show more failed. */
function moreFailed<T>(now: Held<T>, asked: string, error: unknown): Held<T> {
  if (now.key !== asked || now.pages.kind !== "ready") return now;
  return { ...now, pages: { ...now.pages, more: toFailure(error).code } };
}

/**
 * A keyset-paged list (D19): the first page once per `key` (a new search or
 * filter starts over), then `showMore()` appends the page after `next`. A page
 * that arrives after the key changed is dropped. `more` holds the error code
 * of a failed Show more, so the list already shown stays.
 */
export function usePages<T>(
  load: (cursor: number | null) => Promise<Page<T>>,
  key: string,
): {
  pages: Pages<T>;
  showMore: () => void;
  replace: (match: (item: T) => boolean, item: T) => void;
} {
  const [held, setHeld] = useState<Held<T>>({ key, pages: { kind: "loading" } });
  const busy = useRef(false);

  useEffect(() => {
    let live = true;
    setHeld({ key, pages: { kind: "loading" } });
    load(null).then(
      (page) => {
        if (live) setHeld({ key, pages: { kind: "ready", ...page, more: null } });
      },
      (error: unknown) => {
        if (live) setHeld({ key, pages: { kind: "failed", ...toFailure(error) } });
      },
    );
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `load` is new every render; `key` decides when to start over
  }, [key]);

  const pages = held.key === key ? held.pages : ({ kind: "loading" } as const);

  function showMore() {
    if (pages.kind !== "ready" || pages.next === null || busy.current) return;
    busy.current = true;
    load(pages.next)
      .then(
        (page) => setHeld((now) => appended(now, key, page)),
        (error: unknown) => setHeld((now) => moreFailed(now, key, error)),
      )
      .finally(() => {
        busy.current = false;
      });
  }

  const replace = useCallback((match: (item: T) => boolean, item: T) => {
    setHeld((now) =>
      now.pages.kind === "ready"
        ? {
            ...now,
            pages: { ...now.pages, items: now.pages.items.map((x) => (match(x) ? item : x)) },
          }
        : now,
    );
  }, []);

  return { pages, showMore, replace };
}
