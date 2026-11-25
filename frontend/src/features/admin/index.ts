// Public surface of the admin feature (super admin console, M1-06).
export {
  AUDIT_KINDS,
  allInvites,
  auditLog,
  companies,
  company,
  consoleCompanyBase,
  people,
  resumeCompany,
  server,
  suspendCompany,
  workspaceDomains,
  type AuditKind,
  type CompanySummary,
} from "./api";
export { usePages } from "./hooks/usePages";
export { AllInvitesTable } from "./components/AllInvitesTable";
export { AuditList } from "./components/AuditList";
export { CompaniesTable } from "./components/CompaniesTable";
export { DeleteCompanyDialog } from "./components/DeleteCompanyDialog";
export { NewCompanyDialog } from "./components/NewCompanyDialog";
export { PeopleTable } from "./components/PeopleTable";
export { ServerPanel } from "./components/ServerPanel";
export { WorkspaceDomains } from "./components/WorkspaceDomains";
export { LoadFailed, Loading, PageHead, StatusPill } from "./components/parts";
export { MoreButton } from "./components/MoreButton";
