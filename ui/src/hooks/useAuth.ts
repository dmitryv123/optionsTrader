// src/hooks/useAuth.ts
import { useMutation, type MutationFunction } from "@tanstack/react-query";
import { api } from "../lib/api";
import { token } from "../lib/token";

export type AuthResponse = { access: string; refresh: string };
export type LoginVars = { username: string; password: string };

const loginMutationFn: MutationFunction<AuthResponse, LoginVars> = async (vars) => {
  const res = await api.post<AuthResponse>("/api/auth/token/", vars);
  const data = res.data;
  token.setAccess(data.access);
  token.setRefresh(data.refresh);
  return data;
};

const logoutMutationFn: MutationFunction<void, void> = async () => {
  token.clear();
};

export function useLogin() {
  return useMutation<AuthResponse, Error, LoginVars>({ mutationFn: loginMutationFn });
}

export function useLogout() {
  return useMutation<void, Error, void>({ mutationFn: logoutMutationFn });
}





// import { useMutation, type UseMutationOptions, type UseMutationResult } from "@tanstack/react-query";
// import { api } from "../lib/api";
// import { token } from "../lib/token";
//
// /** JWT response shape from /api/auth/token/ */
// export type AuthResponse = { access: string; refresh: string };
//
// /** Variables the login mutation expects */
// export type LoginVars = { username: string; password: string };
//
// /** Login */
// export function useLogin(): UseMutationResult<AuthResponse, Error, LoginVars, unknown> {
//   const options: UseMutationOptions<AuthResponse, Error, LoginVars, unknown> = {
//     mutationFn: async (vars: LoginVars): Promise<AuthResponse> => {
//       const { data } = await api.post<AuthResponse>("/api/auth/token/", vars);
//       token.setAccess(data.access);
//       token.setRefresh(data.refresh);
//       return data;
//     },
//   };
//   return useMutation(options);
// }
//
// /** Logout */
// export function useLogout(): UseMutationResult<void, Error, void, unknown> {
//   const options: UseMutationOptions<void, Error, void, unknown> = {
//     mutationFn: async (): Promise<void> => {
//       token.clear();
//       // optionally: await api.post("/api/auth/logout/") if you implement it
//     },
//   };
//   return useMutation(options);
// }



