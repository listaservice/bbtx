<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  Clock,
  AlertTriangle,
  CheckCircle,
  CreditCard,
  Users,
} from "lucide-vue-next";
import axios from "axios";

interface UserInfo {
  email: string;
  subscription_plan: string;
  subscription_status: string;
  max_teams: number;
  subscription_ends_at: string | null;
}

const userInfo = ref<UserInfo | null>(null);
const loading = ref(true);

onMounted(async () => {
  try {
    const token = localStorage.getItem("auth_token");
    const response = await axios.get("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    userInfo.value = response.data;
  } catch (error) {
    console.error("Failed to load user info:", error);
  } finally {
    loading.value = false;
  }
});

const daysRemaining = computed(() => {
  if (!userInfo.value?.subscription_ends_at) return 0;

  const endDate = new Date(userInfo.value.subscription_ends_at);
  const now = new Date();
  const diff = endDate.getTime() - now.getTime();
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24));

  return Math.max(0, days);
});

const totalDays = computed(() => {
  if (userInfo.value?.subscription_plan === "demo") return 10;
  return 30; // Toate planurile plătite au 30 zile
});

const planName = computed(() => {
  const plans: Record<string, string> = {
    demo: "Demo",
    simplu: "Simplu",
    comun: "Comun",
    extrem: "Extrem",
    premium: "Premium",
  };
  return plans[userInfo.value?.subscription_plan || "demo"] || "Unknown";
});

const planPrice = computed(() => {
  const prices: Record<string, number> = {
    demo: 0,
    simplu: 49,
    comun: 75,
    extrem: 150,
    premium: 250,
  };
  return prices[userInfo.value?.subscription_plan || "demo"] || 0;
});

const isExpiringSoon = computed(
  () => daysRemaining.value <= 3 && daysRemaining.value > 0
);
const isExpired = computed(() => daysRemaining.value === 0);
const isTrial = computed(() => userInfo.value?.subscription_plan === "demo");
const canUpgrade = computed(() => {
  const plan = userInfo.value?.subscription_plan;
  // Premium nu poate face upgrade (e deja maxim)
  return plan && plan !== "demo" && plan !== "premium";
});

const bannerClass = computed(() => {
  if (isExpired.value) return "bg-red-50 border-red-200";
  if (isExpiringSoon.value) return "bg-yellow-50 border-yellow-200";
  if (isTrial.value) return "bg-blue-50 border-blue-200";
  return "bg-green-50 border-green-200";
});

const iconClass = computed(() => {
  if (isExpired.value) return "text-red-600";
  if (isExpiringSoon.value) return "text-yellow-600";
  if (isTrial.value) return "text-blue-600";
  return "text-green-600";
});

const renewalDate = computed(() => {
  if (!userInfo.value?.subscription_ends_at) return "-";
  return new Date(userInfo.value.subscription_ends_at).toLocaleDateString(
    "ro-RO",
    {
      day: "numeric",
      month: "long",
      year: "numeric",
    }
  );
});
</script>

<template>
  <div
    v-if="!loading && userInfo"
    :class="['border rounded-lg p-4 mb-6', bannerClass]"
  >
    <div class="flex items-start justify-between">
      <div class="flex items-start space-x-3 flex-1">
        <!-- Icon -->
        <div :class="['mt-0.5', iconClass]">
          <AlertTriangle v-if="isExpired || isExpiringSoon" class="h-6 w-6" />
          <CheckCircle v-else class="h-6 w-6" />
        </div>

        <!-- Content -->
        <div class="flex-1">
          <!-- Plan Name & Status -->
          <div class="flex items-center space-x-2 mb-2">
            <h3 class="font-semibold text-gray-900">
              {{ isTrial ? "🎁 Trial Gratuit" : `Plan ${planName}` }}
            </h3>
            <span
              v-if="!isTrial"
              class="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800"
            >
              Activ
            </span>
          </div>

          <!-- Days Remaining -->
          <div class="flex items-center space-x-4 text-sm">
            <div class="flex items-center space-x-1.5">
              <Clock class="h-4 w-4 text-gray-500" />
              <span class="text-gray-700">
                <span class="font-semibold">{{ daysRemaining }}</span> zile
                rămase
              </span>
            </div>

            <div class="flex items-center space-x-1.5">
              <Users class="h-4 w-4 text-gray-500" />
              <span class="text-gray-700">
                <span class="font-semibold">{{ userInfo.max_teams }}</span>
                {{ userInfo.max_teams === -1 ? "echipe nelimitate" : "echipe" }}
              </span>
            </div>
          </div>

          <!-- Renewal Date -->
          <div v-if="!isExpired" class="mt-2 text-xs text-gray-600">
            <span v-if="isTrial">Trial se termină pe</span>
            <span v-else>Reînnoire pe</span>
            <span class="font-medium">{{ renewalDate }}</span>
            <span v-if="!isTrial && planPrice > 0"> ({{ planPrice }}€)</span>
          </div>

          <!-- Warning Messages -->
          <div
            v-if="isExpiringSoon"
            class="mt-2 text-sm text-yellow-800 font-medium"
          >
            ⚠️ Abonamentul expiră în curând!
            {{
              isTrial
                ? "Alege un plan pentru a continua."
                : "Asigură-te că plata este configurată."
            }}
          </div>

          <div v-if="isExpired" class="mt-2 text-sm text-red-800 font-medium">
            ❌ Abonamentul a expirat! Contul este suspendat.
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="ml-4 flex flex-col space-y-2">
        <!-- Upgrade button pentru planuri active (nu trial, nu premium) -->
        <router-link
          v-if="canUpgrade && !isExpired && !isExpiringSoon"
          to="/pricing"
          class="inline-flex items-center px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <CreditCard class="h-4 w-4 mr-2" />
          Upgrade Plan
        </router-link>

        <!-- Upgrade/Renew pentru trial, expiring sau expired -->
        <router-link
          v-if="isTrial || isExpiringSoon || isExpired"
          to="/pricing"
          class="inline-flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <CreditCard class="h-4 w-4 mr-2" />
          {{ isTrial ? "Upgrade" : "Reînnoiește" }}
        </router-link>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="mt-3">
      <div class="w-full bg-gray-200 rounded-full h-2">
        <div
          :class="[
            'h-2 rounded-full transition-all duration-300',
            isExpired
              ? 'bg-red-500'
              : isExpiringSoon
              ? 'bg-yellow-500'
              : isTrial
              ? 'bg-blue-500'
              : 'bg-green-500',
          ]"
          :style="{ width: `${(daysRemaining / totalDays) * 100}%` }"
        ></div>
      </div>
    </div>
  </div>
</template>
