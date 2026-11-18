import { useOutletContext } from "react-router";
import type { Company } from "./api";

/** What the company shell gives the pages inside it. */
export interface CompanyContext {
  company: Company;
  companies: Company[];
  /** Load the person's companies again (after their own role changed). */
  reloadCompanies: () => void;
}

/** The company named in the URL, for pages under /c/:slug. */
export function useCompany(): CompanyContext {
  return useOutletContext<CompanyContext>();
}
