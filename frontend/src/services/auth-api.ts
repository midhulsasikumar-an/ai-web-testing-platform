import { API_BASE_URL, type AuthSession } from "@/services/http";

export type SignupResponse = {
  token: string;
  user: {
    id: string;
    name: string;
    email: string;
    role?: string;
  };
};

type MeResponse = {
  user: {
    id: string;
    name: string;
    email: string;
    role?: string;
  };
};

export async function signupWithBackend(name: string, email: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });

  if (!response.ok) {
    const body = await response.text();
    console.error("API Error:", response.status, response.statusText, { url: `${API_BASE_URL}/api/auth/signup`, body });
    throw new Error(`Signup failed: ${response.status} ${response.statusText}`);
  }

  const data = (await response.json()) as SignupResponse;
  return {
    token: data.token,
    user: {
      id: data.user.id,
      name: data.user.name,
      email: data.user.email,
      role: data.user.role,
    },
  };
}

export async function loginWithBackend(email: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const body = await response.text();
    console.error("API Error:", response.status, response.statusText, { url: `${API_BASE_URL}/api/auth/login`, body });
    throw new Error(`Login failed: ${response.status} ${response.statusText}`);
  }

  const data = (await response.json()) as SignupResponse;
  return {
    token: data.token,
    user: {
      id: data.user.id,
      name: data.user.name,
      email: data.user.email,
      role: data.user.role,
    },
  };
}

export async function getCurrentUser(token: string): Promise<MeResponse["user"]> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    console.error("API Error:", response.status, response.statusText, { url: `${API_BASE_URL}/api/auth/me`, body });
    throw new Error(`Session validation failed: ${response.status} ${response.statusText}`);
  }

  const data = (await response.json()) as MeResponse;
  return data.user;
}
