// Change log:
// [#001] 2026-06-22 — Sumeet — File created. App entrypoint: wires TanStack Query (kept from
//        the template stack), the tiny router, auth, and toast providers.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import { AuthProvider } from "./auth"
import "./index.css"
import { RouterProvider } from "./router"
import { ToastProvider } from "./toast"

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
})

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider>
        <ToastProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </ToastProvider>
      </RouterProvider>
    </QueryClientProvider>
  </StrictMode>,
)
