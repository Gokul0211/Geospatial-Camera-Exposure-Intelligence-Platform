"use client";
import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api/errors";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            // An unreachable backend or a 4xx will not fix itself by retrying.
            retry: (count, error) => !(error instanceof ApiError && (error.offline || error.status < 500)) && count < 2,
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <TooltipProvider delayDuration={200}>{children}</TooltipProvider>
    </QueryClientProvider>
  );
}
