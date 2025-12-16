<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  CheckCircle,
  AlertCircle,
  Loader2,
  Key,
  Lock,
  User,
  ExternalLink,
} from "lucide-vue-next";
import axios from "axios";

const router = useRouter();

const currentStep = ref(1);
const loading = ref(false);
const error = ref("");
const success = ref("");

// Step 1: Betfair Credentials
const betfairUsername = ref("");
const betfairPassword = ref("");
const credentialsVerified = ref(false);

// Step 2: App Key (FINAL STEP)
const appKey = ref("");

const canProceedStep1 = computed(() => credentialsVerified.value);
const canProceedStep2 = computed(() => appKey.value.length > 0);

onMounted(async () => {
  // Check if already configured
  try {
    const token = localStorage.getItem("auth_token");
    const response = await axios.get("/api/betfair/credentials-status", {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.data.is_configured) {
      // Already configured, redirect to dashboard
      router.push("/");
    }
  } catch (err) {
    console.error("Failed to check status:", err);
  }
});

async function verifyCredentials() {
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
      "/api/betfair/verify-credentials",
      {
        username: betfairUsername.value,
        password: betfairPassword.value,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (response.data.success) {
      credentialsVerified.value = true;
      success.value = response.data.message;
    } else {
      error.value = response.data.message;
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Eroare la verificare";
  } finally {
    loading.value = false;
  }
}

function nextStep() {
  if (currentStep.value < 2) {
    currentStep.value++;
    error.value = "";
    success.value = "";
  }
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--;
    error.value = "";
    success.value = "";
  }
}

async function saveAndFinish() {
  loading.value = true;
  error.value = "";

  try {
    const token = localStorage.getItem("auth_token");
    const response = await axios.post(
      "/api/betfair/save-credentials",
      {
        username: betfairUsername.value,
        password: betfairPassword.value,
        app_key: appKey.value,
        cert_content: null,
        key_content: null,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (response.data.success) {
      success.value = response.data.message;
      // Redirect to dashboard after 2 seconds
      setTimeout(() => {
        router.push("/");
      }, 2000);
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Eroare la salvare";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-12 px-4">
    <div class="max-w-3xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">
          Configurare Cont Betfair
        </h1>
        <p class="text-gray-600">
          Configurează-ți contul Betfair pentru a folosi bot-ul automat
        </p>
      </div>

      <!-- Progress Steps -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div v-for="step in 2" :key="step" class="flex-1 flex items-center">
            <div
              :class="[
                'w-10 h-10 rounded-full flex items-center justify-center font-semibold',
                currentStep >= step
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-500',
              ]"
            >
              {{ step }}
            </div>
            <div
              v-if="step < 2"
              :class="[
                'flex-1 h-1 mx-2',
                currentStep > step ? 'bg-primary-600' : 'bg-gray-200',
              ]"
            ></div>
          </div>
        </div>
        <div class="flex justify-between mt-2">
          <span class="text-xs text-gray-600">Credențiale Betfair</span>
          <span class="text-xs text-gray-600">App Key (Gratuit)</span>
        </div>
      </div>

      <!-- Card -->
      <div class="bg-white rounded-lg shadow-lg p-8">
        <!-- Success/Error Messages -->
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

        <!-- Step 1: Verify Betfair Credentials -->
        <div v-if="currentStep === 1" class="space-y-6">
          <div>
            <h2 class="text-xl font-semibold text-gray-900 mb-4">
              Step 1: Credențiale Betfair
            </h2>
            <p class="text-gray-600 mb-4">
              Introdu credențialele tale de la Betfair (betfair.ro).
            </p>
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6">
              <p class="text-sm text-blue-800">
                ℹ️ Credențialele vor fi verificate complet când bot-ul rulează
                cu certificatul SSL. Pentru acum, le acceptăm pentru
                configurare.
              </p>
            </div>
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
                :disabled="credentialsVerified"
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
                :disabled="credentialsVerified"
              />
            </div>
          </div>

          <button
            v-if="!credentialsVerified"
            @click="verifyCredentials"
            :disabled="loading"
            class="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center disabled:opacity-50"
          >
            <Loader2 v-if="loading" class="h-5 w-5 animate-spin mr-2" />
            {{ loading ? "Verificare..." : "Verifică Credențialele" }}
          </button>

          <button
            v-if="credentialsVerified"
            @click="nextStep"
            class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center"
          >
            <CheckCircle class="h-5 w-5 mr-2" />
            Continuă la Step 2
          </button>
        </div>

        <!-- Step 2: App Key -->
        <div v-if="currentStep === 2" class="space-y-6">
          <div>
            <h2 class="text-xl font-semibold text-gray-900 mb-4">
              Step 2: Delayed App Key (GRATUIT)
            </h2>
            <p class="text-gray-600 mb-4">
              Obține un <strong>Delayed App Key</strong> gratuit de la Betfair.
              Este instant și nu necesită aprobare!
            </p>

            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <h3 class="font-semibold text-blue-900 mb-2">
                📝 Cum obțin App Key? (Pași Oficiali Betfair)
              </h3>
              <ol
                class="text-sm text-blue-800 space-y-3 list-decimal list-inside"
              >
                <li>
                  <strong>Loghează-te pe Betfair.ro:</strong><br />
                  <a
                    href="https://www.betfair.ro"
                    target="_blank"
                    class="underline font-medium ml-5"
                    >Deschide betfair.ro</a
                  >
                  într-un tab nou și loghează-te<br />
                  <span class="ml-5 text-xs"
                    >⚠️ NU închide tab-ul după login!</span
                  >
                </li>
                <li>
                  <strong>Deschide Demo Tool:</strong><br />
                  <a
                    href="https://apps.betfair.com/visualisers/api-ng-account-operations/"
                    target="_blank"
                    class="underline font-medium ml-5"
                    >Accounts API Demo Tool</a
                  ><br />
                  <span class="ml-5 text-xs">(Se deschide în tab nou)</span>
                </li>
                <li>
                  <strong>În Demo Tool:</strong><br />
                  <span class="ml-5"
                    >• Selectează operația:
                    <strong>createDeveloperAppKeys</strong></span
                  ><br />
                  <span class="ml-5"
                    >• Refresh pagina (F5) → Session Token se completează
                    automat</span
                  ><br />
                  <span class="ml-5"
                    >• Introdu Application Name:
                    <strong>"BetixBot"</strong> (sau alt nume unic)</span
                  ><br />
                  <span class="ml-5"
                    >• Click butonul <strong>"Execute"</strong></span
                  >
                </li>
                <li>
                  <strong>Copiază Delayed App Key:</strong><br />
                  <span class="ml-5"
                    >Betfair generează 2 keys, copiază
                    <strong>Delayed App Key (Active)</strong></span
                  ><br />
                  <span class="ml-5 text-xs">(ex: wKqS7N8xK9xK7N8x)</span>
                </li>
                <li><strong>Lipește-l mai jos</strong> și continuă</li>
              </ol>
              <div class="mt-4 flex flex-col space-y-2">
                <a
                  href="https://www.betfair.ro"
                  target="_blank"
                  class="inline-flex items-center text-blue-700 hover:text-blue-900 font-medium text-sm"
                >
                  <ExternalLink class="h-4 w-4 mr-1" />
                  1. Login Betfair.ro
                </a>
                <a
                  href="https://apps.betfair.com/visualisers/api-ng-account-operations/"
                  target="_blank"
                  class="inline-flex items-center text-blue-700 hover:text-blue-900 font-medium text-sm"
                >
                  <ExternalLink class="h-4 w-4 mr-1" />
                  2. Demo Tool (Generare App Key)
                </a>
              </div>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Delayed App Key
            </label>
            <div class="relative">
              <Key
                class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
              />
              <input
                v-model="appKey"
                type="text"
                class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="wKqS7N8xK9xK7N8x"
              />
            </div>
            <p class="text-xs text-gray-500 mt-1">
              Delayed App Key este gratuit și instant. Nu necesită aprobare.
            </p>
          </div>

          <div class="flex space-x-4">
            <button
              @click="prevStep"
              class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Înapoi
            </button>
            <button
              @click="saveAndFinish"
              :disabled="!canProceedStep2 || loading"
              class="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center disabled:opacity-50"
            >
              <Loader2 v-if="loading" class="h-5 w-5 animate-spin mr-2" />
              {{ loading ? "Salvare..." : "Finalizează Setup" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
