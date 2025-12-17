<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { Lock, Mail, Loader2, AlertCircle } from "lucide-vue-next";
import axios from "axios";

const router = useRouter();

const email = ref("");
const password = ref("");
const isLoading = ref(false);
const error = ref("");

async function handleLogin(): Promise<void> {
  if (!email.value || !password.value) {
    error.value = "Completează toate câmpurile";
    return;
  }

  isLoading.value = true;
  error.value = "";

  try {
    const response = await axios.post("/api/auth/login", {
      email: email.value,
      password: password.value,
    });

    // Noul format de răspuns: { access_token, token_type, user_id, email, ... }
    if (response.data.access_token) {
      localStorage.setItem("auth_token", response.data.access_token);
      localStorage.setItem("user_id", response.data.user_id);
      localStorage.setItem("user_email", response.data.email);
      router.push("/");
    } else {
      error.value = "Autentificare eșuată";
    }
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail;
    } else {
      error.value = "Eroare la conectare. Verifică credențialele.";
    }
    console.error("Login error:", err);
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div
    class="min-h-screen bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center p-4"
  >
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
      <div class="text-center mb-8">
        <img src="/logo.png" alt="Logo" class="h-16 mx-auto mb-4" />
        <h1 class="text-2xl font-bold text-gray-900">Autentificare</h1>
        <p class="text-gray-500 mt-2">
          Introdu credențialele pentru a accesa dashboard-ul
        </p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <div
          v-if="error"
          class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center"
        >
          <AlertCircle class="h-5 w-5 mr-2 flex-shrink-0" />
          {{ error }}
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Email
          </label>
          <div class="relative">
            <Mail
              class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
            />
            <input
              v-model="email"
              type="email"
              class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="admin@betix.com"
              autocomplete="email"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Parolă
          </label>
          <div class="relative">
            <Lock
              class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
            />
            <input
              v-model="password"
              type="password"
              class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="••••••••"
              autocomplete="current-password"
            />
          </div>
        </div>

        <button
          type="submit"
          :disabled="isLoading"
          class="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Loader2 v-if="isLoading" class="h-5 w-5 animate-spin mr-2" />
          {{ isLoading ? "Se autentifică..." : "Intră în cont" }}
        </button>

        <!-- Register Link -->
        <div class="text-center pt-4 border-t border-gray-200">
          <p class="text-sm text-gray-600">
            Nu ai cont?
            <router-link
              to="/register"
              class="text-primary-600 hover:text-primary-700 font-semibold"
            >
              Înregistrează-te gratuit
            </router-link>
          </p>
          <p class="text-xs text-gray-500 mt-2">
            🎁 10 zile trial gratuit cu planul Demo
          </p>
        </div>
      </form>
    </div>
  </div>
</template>
