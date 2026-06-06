import React from "react";
import ReactDOM from "react-dom/client";
import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { Toaster } from "sonner";
import App from "./App";
import { showError } from "./lib/toast";
import "./index.css";

// 401s come from the axios interceptor and trigger their own redirect;
// don't double-toast those. Everything else surfaces as a toast so the
// user always knows when something went wrong.
function shouldToast(error: unknown): boolean {
  const status = (error as { response?: { status?: number } })?.response?.status;
  return status !== 401;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
    mutations: { retry: 0 },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      // Only toast user-initiated refetches / errors that the screen handles
      // poorly; don't shout when the user is just loading a page (the screen
      // already shows an inline error state).
      if (query.state.data !== undefined && shouldToast(error)) {
        showError(error, "Failed to refresh data");
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      if (shouldToast(error)) showError(error);
    },
  }),
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="bottom-right"
        richColors
        closeButton
        duration={4000}
        toastOptions={{
          classNames: {
            toast: "font-sans",
          },
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>,
);
