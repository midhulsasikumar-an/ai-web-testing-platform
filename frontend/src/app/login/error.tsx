"use client";

import { AuthErrorFallback } from "@/components/auth/auth-error-fallback";

export default function LoginError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <AuthErrorFallback
      title="Login page failed"
      message="Something went wrong while rendering login. Network or data errors were handled safely."
      onRetry={reset}
    />
  );
}
