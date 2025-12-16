import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";

interface UserData {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  subscription_plan: string | null;
  subscription_status: string;
  max_teams: number;
  trial_ends_at: string | null;
  subscription_ends_at: string | null;
  google_sheets_id: string | null;
  created_at: string;
  last_login: string | null;
}

export const useUserStore = defineStore("user", () => {
  const user = ref<UserData | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const googleSheetsUrl = computed(() => {
    if (!user.value?.google_sheets_id) return null;
    return `https://docs.google.com/spreadsheets/d/${user.value.google_sheets_id}`;
  });

  const hasGoogleSheets = computed(() => !!user.value?.google_sheets_id);

  async function fetchUser(): Promise<void> {
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    isLoading.value = true;
    error.value = null;

    try {
      const response = await axios.get("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      user.value = response.data;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la încărcarea datelor";
      user.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  function clearUser(): void {
    user.value = null;
  }

  return {
    user,
    isLoading,
    error,
    googleSheetsUrl,
    hasGoogleSheets,
    fetchUser,
    clearUser,
  };
});
