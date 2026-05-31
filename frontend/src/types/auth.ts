export type UserMe = {
  id: string;
  email: string;
  name: string | null;
  provider: string | null;
  provider_account_id: string | null;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer" | string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  password: string;
  name?: string | null;
};

export type OAuthEntryResponse = {
  provider: "google" | "github" | string;
  authorization_url: string;
  state: string;
};
