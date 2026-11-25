import { Navigate, useNavigate, useParams } from "react-router";
import { useMe } from "@/features/auth";
import { useCompany } from "@/features/orgs";
import {
  ProjectHeader,
  ProjectInviteForm,
  ProjectInvitesTable,
  ProjectMembersTable,
  inviteRoles,
  managesMembers,
  project as loadProject,
  projectInvites,
  projectMembers,
} from "@/features/projects";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";
import { Failed, Loading } from "./parts";

// A project's members (prototype Project members): invite, the people with
// their roles, pending invites. Who may do what follows the server's rules;
// anyone else sees why they cannot invite.
export function ProjectMembersPage() {
  const { company } = useCompany();
  const me = useMe();
  const navigate = useNavigate();
  const id = Number(useParams().projectId);
  const slug = company.slug;
  const key = `${slug}:${id}`;
  const [project, reloadProject] = useAsync(() => loadProject(slug, id), `project:${key}`);
  const [people, reloadPeople] = useAsync(() => projectMembers(slug, id), `pmembers:${key}`);
  const [pending, reloadPending] = useAsync(() => projectInvites(slug, id), `pinvites:${key}`);

  const failed = [project, people, pending].find((s) => s.kind === "failed");
  if (failed?.kind === "failed" && failed.status === 401) return <Navigate to="/signin" replace />;
  if (failed?.kind === "failed") {
    return (
      <Failed
        message={errorText(failed.code)}
        onRetry={() => {
          reloadProject();
          reloadPeople();
          reloadPending();
        }}
      />
    );
  }
  if (project.kind !== "ready") return <Loading />;
  const p = project.value;
  const roles = inviteRoles(p, company.role === "owner");
  return (
    <>
      <ProjectHeader
        slug={slug}
        project={p}
        members={people.kind === "ready" ? people.value.length : null}
      />
      <div className="mt-6 flex flex-col gap-5">
        {roles.length > 0 ? (
          <ProjectInviteForm
            slug={slug}
            projectId={id}
            company={company.name}
            roles={roles}
            onInvited={reloadPending}
          />
        ) : (
          !p.archived_at && (
            <p className="rounded-lg bg-sunken px-4 py-3 text-sm text-muted">
              {t("pinvite.notAllowed")}
            </p>
          )
        )}
        {people.kind === "ready" ? (
          <ProjectMembersTable
            slug={slug}
            projectId={id}
            project={p.name}
            members={people.value}
            meId={me.id}
            manages={managesMembers(p)}
            details={p.role === "owner" || company.role === "owner"}
            onChanged={() => {
              reloadPeople();
              reloadProject(); // your own role may have changed
            }}
            onLeft={() => navigate(`/c/${slug}`, { replace: true })}
          />
        ) : (
          <Loading />
        )}
        {pending.kind === "ready" ? (
          <ProjectInvitesTable
            slug={slug}
            projectId={id}
            invites={pending.value}
            revocable={roles}
            onChanged={reloadPending}
          />
        ) : (
          <Loading />
        )}
      </div>
    </>
  );
}
