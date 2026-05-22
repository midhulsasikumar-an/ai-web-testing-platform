"use client";

import { AuthErrorFallback } from "@/components/auth/auth-error-fallback";

export default function SignupError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <AuthErrorFallback
      title="Signup page failed"
      message="Something went wrong while rendering signup. Network or data errors were handled safely."
      onRetry={reset}
    />
  );
}
