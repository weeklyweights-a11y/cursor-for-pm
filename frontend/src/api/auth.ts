import type { AuthResponse, LoginResponse, User } from "../types/auth";
import { apiClient, setStoredToken } from "./client";

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<{ data: LoginResponse }>("/api/v1/auth/login", {
    email,
    password,
  });
  setStoredToken(data.data.access_token);
  return data.data;
}

export async function signupUser(
  name: string,
  email: string,
  password: string,
  organizationName: string
): Promise<AuthResponse> {
  const { data } = await apiClient.post<{ data: AuthResponse }>("/api/v1/auth/signup", {
    name,
    email,
    password,
    organization_name: organizationName,
  });
  setStoredToken(data.data.access_token);
  return data.data;
}

export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<{ data: User }>("/api/v1/auth/me");
  return data.data;
}
