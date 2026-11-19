import { createBrowserRouter, type RouteObject } from "react-router";
import { CompaniesPage } from "@/pages/admin/CompaniesPage";
import { CompanyPage } from "@/pages/admin/CompanyPage";
import { CompanyHomePage } from "@/pages/company/CompanyHomePage";
import { CompanySettingsPage } from "@/pages/company/CompanySettingsPage";
import { HomePage } from "@/pages/home/HomePage";
import { NotFoundPage } from "@/pages/not-found/NotFoundPage";
import { RefusedPage } from "@/pages/signin/RefusedPage";
import { SignInPage } from "@/pages/signin/SignInPage";
import { AdminLayout } from "./layouts/AdminLayout";
import { AppLayout } from "./layouts/AppLayout";
import { CompanyLayout } from "./layouts/CompanyLayout";

// Screen routes are added per milestone (see design/README.md for the index).
// Heavy screens (card dialog, table, dashboard) are loaded with `lazy` to keep
// the initial bundle under budget.
export const routes: RouteObject[] = [
  { path: "/signin", element: <SignInPage /> },
  { path: "/signin/refused", element: <RefusedPage /> },
  {
    path: "/",
    element: <AppLayout />,
    children: [{ index: true, element: <HomePage /> }],
  },
  {
    // One company: its slug is the address (`/c/harbor`), as in the prototype.
    path: "/c/:slug",
    element: <CompanyLayout />,
    children: [
      { index: true, element: <CompanyHomePage /> },
      { path: "settings", element: <CompanySettingsPage /> },
    ],
  },
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [
      { index: true, element: <CompaniesPage /> },
      { path: "companies/:slug", element: <CompanyPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];

export const router = createBrowserRouter(routes);
