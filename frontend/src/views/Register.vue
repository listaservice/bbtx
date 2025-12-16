<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  Mail,
  Lock,
  User,
  Loader2,
  AlertCircle,
  CheckCircle,
} from "lucide-vue-next";
import axios from "axios";

const router = useRouter();

const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const fullName = ref("");
const isLoading = ref(false);
const error = ref("");
const success = ref(false);

async function handleRegister(): Promise<void> {
  // Reset states
  error.value = "";
  success.value = false;

  // Validare
  if (!email.value || !password.value || !confirmPassword.value) {
    error.value = "Completează toate câmpurile obligatorii";
    return;
  }

  if (password.value.length < 8) {
    error.value = "Parola trebuie să aibă minim 8 caractere";
    return;
  }

  if (password.value !== confirmPassword.value) {
    error.value = "Parolele nu se potrivesc";
    return;
  }

  isLoading.value = true;

  try {
    const response = await axios.post("/api/auth/register", {
      email: email.value,
      password: password.value,
      full_name: fullName.value || null,
    });

    if (response.data) {
      success.value = true;

      // Redirect la login după 2 secunde
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    }
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail;
    } else {
      error.value = "Eroare la înregistrare. Încearcă din nou.";
    }
    console.error("Register error:", err);
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
        <h1 class="text-3xl font-bold text-gray-900">Înregistrare</h1>
        <p class="text-gray-500 mt-2">
          Creează cont și primești
          <span class="font-semibold text-primary-600"
            >3 zile trial gratuit</span
          >
        </p>
        <div
          class="mt-4 bg-primary-50 border border-primary-200 rounded-lg p-3"
        >
          <p class="text-sm text-primary-800 font-medium">
            🎁 Plan Demo: 5 echipe gratuit pentru 3 zile!
          </p>
        </div>
      </div>

      <form @submit.prevent="handleRegister" class="space-y-5">
        <!-- Success Message -->
        <div
          v-if="success"
          class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center"
        >
          <CheckCircle class="h-5 w-5 mr-2 flex-shrink-0" />
          <div>
            <p class="font-medium">Cont creat cu succes!</p>
            <p class="text-sm">Redirecționare către login...</p>
          </div>
        </div>

        <!-- Error Message -->
        <div
          v-if="error"
          class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center"
        >
          <AlertCircle class="h-5 w-5 mr-2 flex-shrink-0" />
          {{ error }}
        </div>

        <!-- Email -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Email <span class="text-red-500">*</span>
          </label>
          <div class="relative">
            <Mail
              class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
            />
            <input
              v-model="email"
              type="email"
              class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="exemplu@email.com"
              autocomplete="email"
              required
            />
          </div>
        </div>

        <!-- Full Name (optional) -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Nume complet <span class="text-gray-400 text-xs">(opțional)</span>
          </label>
          <div class="relative">
            <User
              class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
            />
            <input
              v-model="fullName"
              type="text"
              class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="Ion Popescu"
              autocomplete="name"
            />
          </div>
        </div>

        <!-- Password -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Parolă <span class="text-red-500">*</span>
          </label>
          <div class="relative">
            <Lock
              class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
            />
            <input
              v-model="password"
              type="password"
              class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="Minim 8 caractere"
              autocomplete="new-password"
              required
            />
          </div>
          <p class="text-xs text-gray-500 mt-1">Minim 8 caractere</p>
        </div>

        <!-- Confirm Password -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Confirmă parola <span class="text-red-500">*</span>
          </label>
          <div class="relative">
            <Lock
              class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
            />
            <input
              v-model="confirmPassword"
              type="password"
              class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="Repetă parola"
              autocomplete="new-password"
              required
            />
          </div>
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="isLoading || success"
          class="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Loader2 v-if="isLoading" class="h-5 w-5 animate-spin mr-2" />
          {{ isLoading ? "Se creează contul..." : "Creează cont gratuit" }}
        </button>

        <!-- Login Link -->
        <div class="text-center pt-4 border-t border-gray-200">
          <p class="text-sm text-gray-600">
            Ai deja cont?
            <router-link
              to="/login"
              class="text-primary-600 hover:text-primary-700 font-semibold"
            >
              Intră în cont
            </router-link>
          </p>
        </div>
      </form>

      <!-- Trial Info -->
      <div class="mt-6 text-center">
        <p class="text-xs text-gray-500">
          Prin înregistrare, primești automat 3 zile de trial gratuit cu planul
          Demo (5 echipe).
        </p>
      </div>
    </div>
  </div>
</template>
