import { RouterProvider } from "react-router";
import { router } from "./router";

// App-wide providers wrap the router here as they arrive (session, theme from
// personal settings, realtime connection).
export function App() {
  return <RouterProvider router={router} />;
}
