import { createBrowserRouter, type RouteObject } from "react-router";
import { AdminHomePage } from "@/pages/admin/AdminHomePage";
import { HomePage } from "@/pages/home/HomePage";
import { NotFoundPage } from "@/pages/not-found/NotFoundPage";
import { SignInPage } from "@/pages/signin/SignInPage";
import { AdminLayout } from "./layouts/AdminLayout";
import { AppLayout } from "./layouts/AppLayout";

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
    children: [{ index: true, element: <AdminHomePage /> }],
  },
  { path: "*", element: <NotFoundPage /> },
];

export const router = createBrowserRouter(routes);
