import { computed, ref } from "vue";

// Placeholder local auth state until the backend's Keycloak login flow
// (issue #3) is wired up: toggles a fake session so the header/profile UI
// can be built and reviewed independently.
const isAuthenticated = ref(false);
const userName = ref("Agent instructeur");

export function useAuth() {
  const login = () => {
    isAuthenticated.value = true;
  };

  const logout = () => {
    isAuthenticated.value = false;
  };

  return {
    isAuthenticated: computed(() => isAuthenticated.value),
    userName: computed(() => userName.value),
    login,
    logout,
  };
}
