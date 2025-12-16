<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { Check, Zap, Crown } from "lucide-vue-next";
import axios from "axios";

interface UserInfo {
  subscription_plan: string;
  subscription_status: string;
}

const userInfo = ref<UserInfo | null>(null);
const loading = ref(true);

onMounted(async () => {
  try {
    const token = localStorage.getItem("auth_token");
    if (token) {
      const response = await axios.get("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      userInfo.value = response.data;
    }
  } catch (error) {
    console.error("Failed to load user info:", error);
  } finally {
    loading.value = false;
  }
});

const currentPlan = computed(() => userInfo.value?.subscription_plan || "demo");

function isCurrentPlan(planName: string): boolean {
  return currentPlan.value === planName.toLowerCase();
}

function canUpgradeTo(planName: string): boolean {
  const planOrder = ["demo", "simplu", "comun", "extrem", "premium"];
  const currentIndex = planOrder.indexOf(currentPlan.value);
  const targetIndex = planOrder.indexOf(planName.toLowerCase());
  return targetIndex > currentIndex;
}

const plans = [
  {
    name: "Simplu",
    price: 49,
    teams: 5,
    popular: false,
    features: [
      "5 echipe active",
      "Bot automat zilnic",
      "Google Sheets dedicat",
      "Progression strategy",
      "Support email",
    ],
  },
  {
    name: "Comun",
    price: 75,
    teams: 10,
    popular: true,
    features: [
      "10 echipe active",
      "Bot automat zilnic",
      "Google Sheets dedicat",
      "Progression strategy",
      "Support prioritar",
      "Statistici avansate",
    ],
  },
  {
    name: "Extrem",
    price: 150,
    teams: 25,
    popular: false,
    features: [
      "25 echipe active",
      "Bot automat zilnic",
      "Google Sheets dedicat",
      "Progression strategy",
      "Support 24/7",
      "Statistici avansate",
      "API access",
    ],
  },
  {
    name: "Premium",
    price: 250,
    teams: -1,
    popular: false,
    features: [
      "Echipe nelimitate",
      "Bot automat zilnic",
      "Google Sheets dedicat",
      "Progression strategy",
      "Support dedicat",
      "Statistici avansate",
      "API access",
      "Custom features",
    ],
  },
];
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-12">
    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">
        Alege Planul Potrivit
      </h1>
      <p class="text-xl text-gray-600">
        Toate planurile includ 30 de zile de acces complet
      </p>
    </div>

    <!-- Plans Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div
        v-for="plan in plans"
        :key="plan.name"
        :class="[
          'relative bg-white rounded-2xl shadow-lg border-2 transition-all hover:shadow-xl',
          isCurrentPlan(plan.name)
            ? 'border-green-500 scale-105'
            : plan.popular
            ? 'border-primary-500 scale-105'
            : 'border-gray-200',
        ]"
      >
        <!-- Current Plan Badge -->
        <div
          v-if="isCurrentPlan(plan.name)"
          class="absolute -top-4 left-1/2 -translate-x-1/2 bg-green-600 text-white px-4 py-1 rounded-full text-sm font-semibold flex items-center space-x-1"
        >
          <Crown class="h-4 w-4" />
          <span>Planul Tău</span>
        </div>

        <!-- Popular Badge -->
        <div
          v-else-if="plan.popular"
          class="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary-600 text-white px-4 py-1 rounded-full text-sm font-semibold flex items-center space-x-1"
        >
          <Zap class="h-4 w-4" />
          <span>Popular</span>
        </div>

        <div class="p-6">
          <!-- Plan Name -->
          <h3 class="text-2xl font-bold text-gray-900 mb-2">{{ plan.name }}</h3>

          <!-- Price -->
          <div class="mb-6">
            <span class="text-4xl font-bold text-gray-900"
              >{{ plan.price }}€</span
            >
            <span class="text-gray-600">/lună</span>
          </div>

          <!-- Teams -->
          <div class="mb-6 text-gray-700">
            <span class="font-semibold">
              {{ plan.teams === -1 ? "Nelimitat" : plan.teams }}
            </span>
            echipe
          </div>

          <!-- Features -->
          <ul class="space-y-3 mb-8">
            <li
              v-for="feature in plan.features"
              :key="feature"
              class="flex items-start space-x-2"
            >
              <Check class="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
              <span class="text-sm text-gray-700">{{ feature }}</span>
            </li>
          </ul>

          <!-- CTA Button -->
          <button
            v-if="isCurrentPlan(plan.name)"
            class="w-full py-3 px-4 rounded-lg font-semibold bg-green-100 text-green-800 cursor-not-allowed"
            disabled
          >
            Planul Curent
          </button>
          <button
            v-else-if="canUpgradeTo(plan.name)"
            :class="[
              'w-full py-3 px-4 rounded-lg font-semibold transition-colors',
              'bg-purple-600 hover:bg-purple-700 text-white',
            ]"
            disabled
          >
            Upgrade (În curând)
          </button>
          <button
            v-else
            class="w-full py-3 px-4 rounded-lg font-semibold bg-gray-100 text-gray-500 cursor-not-allowed"
            disabled
          >
            Nu disponibil
          </button>
        </div>
      </div>
    </div>

    <!-- Info -->
    <div class="mt-12 text-center">
      <p class="text-gray-600">
        🎁 Încearcă gratuit 3 zile cu planul Demo (5 echipe)
      </p>
      <p class="text-sm text-gray-500 mt-2">
        Toate planurile se reînnoiesc automat la fiecare 30 de zile
      </p>
    </div>
  </div>
</template>
