import { computed, ref } from "vue";

import { apiFetch } from "@/utils/api";

// Auth BFF : le navigateur ne parle jamais directement à Keycloak. Le bouton
// "Se connecter" redirige vers /api/auth/login (backend), qui initie le flow
// OAuth2+PKCE et revient via /api/auth/callback. La session est portée par un
// cookie HttpOnly posé par le backend - le frontend n'a jamais le token.

interface UserProfile {
  userId: string;
  email: string;
  firstName: string;
  lastName: string;
  roles: string[];
  isAdmin: boolean;
}

const profile = ref<UserProfile | null>(null);
const loading = ref(false);

const displayName = computed(() => {
  if (!profile.value) return "";
  const { firstName, lastName, email } = profile.value;
  if (firstName || lastName) return [firstName, lastName].filter(Boolean).join(" ");
  return email;
});

export function useAuth() {
  // Au montage de l'app, on interroge /api/auth/me pour savoir si une
  // session est déjà active (cookie HttpOnly envoyé automatiquement). Une
  // 401 silencieuse signifie "non connecté", pas une erreur à afficher.
  const fetchProfile = async () => {
    loading.value = true;
    try {
      profile.value = await apiFetch<UserProfile>("/api/auth/me");
    } catch {
      profile.value = null;
    } finally {
      loading.value = false;
    }
  };

  const login = () => {
    // Redirige le navigateur vers le backend, qui le redirige à son tour
    // vers Keycloak. On lit le paramètre `redirect` de l'URL (posé par le
    // route guard quand il redirige vers /welcome) pour revenir sur la page
    // demandée après login. Sinon, on revient sur /analyses.
    const params = new URLSearchParams(window.location.search);
    const current = params.get("redirect") ?? "/analyses";
    window.location.href = `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/api/auth/login?redirect=${encodeURIComponent(current)}`;
  };

  const logout = async () => {
    try {
      const data = await apiFetch<{ redirectUrl: string }>("/api/auth/logout", { method: "POST" });
      // Le backend renvoie l'URL de logout Keycloak (RP-initiated logout) :
      // le navigateur y va pour fermer aussi la session SSO.
      window.location.href = data.redirectUrl;
    } catch {
      // En cas d'échec, on dégrade au moins l'état local.
      profile.value = null;
    }
  };

  return {
    isAuthenticated: computed(() => profile.value !== null),
    userName: displayName,
    isAdmin: computed(() => profile.value?.isAdmin ?? false),
    profile: computed(() => profile.value),
    loading: computed(() => loading.value),
    fetchProfile,
    login,
    logout,
  };
}
