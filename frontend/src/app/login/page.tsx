"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  
  useEffect(() => {
    // The login page is now at the root route '/'
    router.replace("/");
  }, [router]);

  return null;
}
