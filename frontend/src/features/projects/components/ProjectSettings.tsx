import { useState, type ReactNode, type SubmitEvent } from "react";
import { Link } from "react-router";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { BOARD_BACKGROUNDS } from "@/shared/lib/backgrounds";
import { Switch } from "@/shared/ui/Switch";
import { updateProject, type AgingDays, type Project, type ProjectChanges } from "../api";
import { PROJECT_COLORS } from "./ProjectBadge";

const AGING_DAYS: AgingDays[] = [3, 7, 14, 30];

/** Project settings for project owners (prototype Project settings): General
 * saves with its button; the switches and card aging save as they change.
 * An archived project shows every field read-only. */
export function ProjectSettings({
  slug,
  project,
  companyOwner,
  onSaved,
}: {
  slug: string;
  project: Project;
  companyOwner: boolean;
  onSaved: (project: Project) => void;
}) {
  const readOnly = project.archived_at !== null;
  const [problem, setProblem] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function save(changes: ProjectChanges) {
    setProblem(null);
    setSaved(false);
    try {
      onSaved(await updateProject(slug, project.id, changes));
      return true;
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
      return false;
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {problem && (
        <p role="alert" className="text-sm text-danger">
          {problem}
        </p>
      )}
      <General
        project={project}
        readOnly={readOnly}
        saved={saved}
        onSave={async (changes) => setSaved(await save(changes))}
      />
      <Box title={t("psettings.permissions")}>
        <Toggle
          label={t("psettings.membersCreateBoards")}
          hint={t("psettings.membersCreateBoardsHint")}
          on={project.members_can_create_boards}
          disabled={readOnly}
          onToggle={() =>
            void save({ members_can_create_boards: !project.members_can_create_boards })
          }
        />
        <Toggle
          label={t("psettings.membersInvite")}
          hint={t("psettings.membersInviteHint")}
          on={project.members_can_invite}
          disabled={readOnly}
          onToggle={() => void save({ members_can_invite: !project.members_can_invite })}
        />
      </Box>
      <Box title={t("psettings.aging")}>
        <Toggle
          label={t("psettings.agingFade")}
          hint={t("psettings.agingHint")}
          on={project.aging_enabled}
          disabled={readOnly}
          onToggle={() => void save({ aging_enabled: !project.aging_enabled })}
        />
        {project.aging_enabled && (
          <div className="flex flex-col gap-3 pt-4">
            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              {t("psettings.agingAfter")}
              <select
                value={project.aging_days}
                disabled={readOnly}
                onChange={(e) => void save({ aging_days: Number(e.target.value) as AgingDays })}
                className="h-10 w-64 rounded-md border border-line bg-surface px-3 font-normal"
              >
                {AGING_DAYS.map((days) => (
                  <option key={days} value={days}>
                    {t(days === 7 ? "psettings.daysDefault" : "psettings.days", { days })}
                  </option>
                ))}
              </select>
            </label>
            <AgingPreview days={project.aging_days} />
          </div>
        )}
      </Box>
      <section className="rounded-xl border border-danger p-5">
        <h2 className="text-lg font-semibold">{t("psettings.archiveTitle")}</h2>
        <p className="mt-2 text-sm text-muted">
          {t("psettings.archiveText")}
          {companyOwner && (
            <>
              {" "}
              {t("psettings.archiveFrom")}{" "}
              <Link to={`/c/${slug}/manage`} className="text-accent underline">
                {t("nav.manage")}
              </Link>
              .
            </>
          )}
        </p>
      </section>
    </div>
  );
}

function General({
  project,
  readOnly,
  saved,
  onSave,
}: {
  project: Project;
  readOnly: boolean;
  saved: boolean;
  onSave: (changes: ProjectChanges) => Promise<void>;
}) {
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description);
  const [color, setColor] = useState(project.color);
  const [background, setBackground] = useState(project.default_background);
  const [busy, setBusy] = useState(false);

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const changes: ProjectChanges = {};
    if (name.trim() !== project.name) changes.name = name.trim();
    if (description !== project.description) changes.description = description;
    if (color !== project.color) changes.color = color;
    if (background !== project.default_background) changes.default_background = background;
    if (Object.keys(changes).length === 0) return;
    setBusy(true);
    await onSave(changes);
    setBusy(false);
  }

  const swatch = (on: boolean) =>
    `h-9 w-11 rounded-md border-2 ${on ? "border-accent" : "border-transparent"} disabled:opacity-60`;
  return (
    <Box title={t("psettings.general")}>
      <form onSubmit={submit} className="flex flex-col gap-4 text-sm">
        <label className="flex flex-col gap-1.5 font-semibold">
          {t("psettings.name")}
          <input
            required
            maxLength={100}
            value={name}
            disabled={readOnly}
            onChange={(e) => setName(e.target.value)}
            className="h-10 rounded-md border border-line bg-surface px-3 font-normal"
          />
        </label>
        <label className="flex flex-col gap-1.5 font-semibold">
          {t("psettings.description")}
          <input
            maxLength={2000}
            value={description}
            disabled={readOnly}
            onChange={(e) => setDescription(e.target.value)}
            className="h-10 rounded-md border border-line bg-surface px-3 font-normal"
          />
        </label>
        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1.5 font-semibold">{t("psettings.color")}</legend>
          <div className="flex gap-2">
            {PROJECT_COLORS.map((key) => (
              <button
                key={key}
                type="button"
                aria-label={t("psettings.colorOption", { key })}
                aria-pressed={color === key}
                disabled={readOnly}
                onClick={() => setColor(key)}
                className={`tone-${key} ${swatch(color === key)}`}
              />
            ))}
          </div>
        </fieldset>
        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1.5 font-semibold">{t("psettings.background")}</legend>
          <div className="flex flex-wrap gap-2">
            {BOARD_BACKGROUNDS.map((key) => (
              <button
                key={key}
                type="button"
                aria-label={t("psettings.backgroundOption", { key })}
                aria-pressed={background === key}
                disabled={readOnly}
                onClick={() => setBackground(key)}
                className={`board-bg-${key} ${swatch(background === key)}`}
              />
            ))}
          </div>
        </fieldset>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={readOnly || busy}
            className="h-10 self-start rounded-md bg-accent px-4 font-semibold text-white disabled:opacity-60"
          >
            {t("psettings.save")}
          </button>
          {saved && (
            <span role="status" className="text-success">
              {t("psettings.saved")}
            </span>
          )}
        </div>
      </form>
    </Box>
  );
}

function Box({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Toggle(props: {
  label: string;
  hint: string;
  on: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center gap-4 border-b border-line py-3 last:border-b-0">
      <span className="flex-1">
        <span className="block font-semibold">{props.label}</span>
        <span className="block text-sm text-muted">{props.hint}</span>
      </span>
      <Switch
        on={props.on}
        label={props.label}
        disabled={props.disabled}
        onToggle={props.onToggle}
      />
    </div>
  );
}

/** What fading looks like after `days` (the prototype's four sample cards). */
function AgingPreview({ days }: { days: number }) {
  const steps = [
    { text: t("psettings.agingActive"), fade: "" },
    { text: t("psettings.agingQuiet", { days }), fade: "opacity-80" },
    { text: t("psettings.agingQuiet", { days: days * 2 }), fade: "opacity-60" },
    { text: t("psettings.agingQuiet", { days: days * 3 }), fade: "opacity-40" },
  ];
  return (
    <div aria-hidden="true" className="grid grid-cols-4 gap-2 rounded-lg bg-sunken p-2 text-sm">
      {steps.map((s) => (
        <span key={s.text} className={`rounded-md bg-surface px-3 py-2 shadow-sm ${s.fade}`}>
          {s.text}
        </span>
      ))}
    </div>
  );
}
