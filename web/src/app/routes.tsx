import type { RouteObject } from "react-router";
import { AdminLayout } from "@/admin/AdminLayout";
import { AppLayout } from "./AppLayout";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SignInPage } from "./pages/SignInPage";

// Screen routes are added per milestone (see design/README.md for the index).
// Heavy screens (card dialog, table, dashboard) are loaded with `lazy` to keep
// the initial bundle under budget.
export const routes: RouteObject[] = [
  { path: "/signin", element: <SignInPage /> },
  {
    path: "/",
    element: <AppLayout />,
    children: [{ index: true, element: <HomePage /> }],
  },
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [{ index: true, element: <p className="text-muted">Admin console (M1-06)</p> }],
  },
  { path: "*", element: <NotFoundPage /> },
];
