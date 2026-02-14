export interface User {
  id: string;
  email: string;
  name: string;
  org_id: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  user: User;
  organization: Organization;
  access_token: string;
  token_type: string;
}

export interface LoginResponse {
  user: User;
  access_token: string;
  token_type: string;
}
