<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { CheckCircle, AlertCircle, Loader2, Lock, User } from "lucide-vue-next";
import axios from "axios";

const router = useRouter();

const loading = ref(false);
const error = ref("");
const success = ref("");

const betfairUsername = ref("");
const betfairPassword = ref("");

onMounted(async () => {
  try {
    const token = localStorage.getItem("auth_token");
    const response = await axios.get("/api/betfair/credentials-status", {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.data.is_configured) {
      router.push("/");
    }
  } catch (err) {
    console.error("Failed to check status:", err);
  }
});

async function setupBetfair() {
  if (!betfairUsername.value || !betfairPassword.value) {
    error.value = "Completează username și parola Betfair";
    return;
  }

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const token = localStorage.getItem("auth_token");
    const response = await axios.post(
      "/api/betfair/generate-app-key",
      {
        username: betfairUsername.value,
        password: betfairPassword.value,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (response.data.success) {
      success.value = response.data.message;
      setTimeout(() => {
        router.push("/");
      }, 2000);
    } else {
      error.value = response.data.message;
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Eroare la configurare";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-12 px-4">
    <div class="max-w-xl mx-auto">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">
          Configurare Cont Betfair
        </h1>
        <p class="text-gray-600">
          Introdu credențialele tale Betfair și noi generăm automat App Key-ul
        </p>
      </div>

      <div class="bg-white rounded-lg shadow-lg p-8">
        <div
          v-if="success"
          class="mb-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center"
        >
          <CheckCircle class="h-5 w-5 mr-2 flex-shrink-0" />
          {{ success }}
        </div>

        <div
          v-if="error"
          class="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center"
        >
          <AlertCircle class="h-5 w-5 mr-2 flex-shrink-0" />
          {{ error }}
        </div>

        <div class="space-y-6">
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p class="text-sm text-blue-800">
              🔒 Credențialele tale sunt criptate și securizate. Le folosim doar
              pentru a genera App Key-ul tău personal Betfair.
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Username Betfair
            </label>
            <div class="relative">
              <User
                class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
              />
              <input
                v-model="betfairUsername"
                type="text"
                class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="username@email.com"
                :disabled="loading"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Parolă Betfair
            </label>
            <div class="relative">
              <Lock
                class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
              />
              <input
                v-model="betfairPassword"
                type="password"
                class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="••••••••"
                :disabled="loading"
              />
            </div>
          </div>

          <button
            @click="setupBetfair"
            :disabled="loading || !betfairUsername || !betfairPassword"
            class="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center disabled:opacity-50"
          >
            <Loader2 v-if="loading" class="h-5 w-5 animate-spin mr-2" />
            {{ loading ? "Se configurează..." : "Configurează Betfair" }}
          </button>

          <p class="text-xs text-gray-500 text-center">
            Vom face login pe Betfair și vom genera automat App Key-ul tău.
            Acest proces durează câteva secunde.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
