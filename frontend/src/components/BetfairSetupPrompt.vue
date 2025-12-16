<script setup lang="ts">
import { ref, onMounted } from "vue";
import { AlertTriangle, Settings } from "lucide-vue-next";
import axios from "axios";

const isConfigured = ref(true);
const loading = ref(true);

onMounted(async () => {
  try {
    const token = localStorage.getItem("auth_token");
    const response = await axios.get("/api/betfair/credentials-status", {
      headers: { Authorization: `Bearer ${token}` },
    });

    isConfigured.value = response.data.is_configured;
  } catch (error) {
    console.error("Failed to check Betfair status:", error);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div
    v-if="!loading && !isConfigured"
    class="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6"
  >
    <div class="flex items-start justify-between">
      <div class="flex items-start space-x-3 flex-1">
        <AlertTriangle class="h-6 w-6 text-orange-600 flex-shrink-0 mt-0.5" />
        <div class="flex-1">
          <h3 class="font-semibold text-orange-900 mb-1">
            Configurare Betfair Necesară
          </h3>
          <p class="text-sm text-orange-800 mb-3">
            Pentru a folosi bot-ul automat, trebuie să configurezi contul tău
            Betfair. Procesul durează doar 30 de secunde și este complet
            gratuit!
          </p>
          <router-link
            to="/betfair-setup"
            class="inline-flex items-center px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Settings class="h-4 w-4 mr-2" />
            Configurează Acum
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
