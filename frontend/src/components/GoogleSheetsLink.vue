<script setup lang="ts">
import { onMounted } from "vue";
import { FileSpreadsheet, ExternalLink, AlertTriangle } from "lucide-vue-next";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();

onMounted(() => {
  userStore.fetchUser();
});
</script>

<template>
  <div v-if="userStore.hasGoogleSheets">
    <!-- Google Sheets Link -->
    <div class="bg-green-50 border border-green-200 rounded-xl p-4">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center space-x-3">
          <div class="p-2 bg-green-100 rounded-lg">
            <FileSpreadsheet class="h-6 w-6 text-green-600" />
          </div>
          <div>
            <h3 class="font-semibold text-green-800">Google Sheets</h3>
            <p class="text-sm text-green-600">
              Vizualizează meciurile și statisticile tale
            </p>
          </div>
        </div>
        <a
          :href="userStore.googleSheetsUrl!"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center space-x-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          <span>Deschide</span>
          <ExternalLink class="h-4 w-4" />
        </a>
      </div>

      <!-- Avertizare Securitate -->
      <div
        class="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start space-x-2"
      >
        <AlertTriangle class="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
        <p class="text-xs text-red-700">
          <span class="font-semibold">⚠️ IMPORTANT:</span> NU partaja link-ul
          Google Sheets cu nimeni! Oricine are link-ul poate vedea și șterge
          toate echipele și datele tale.
        </p>
      </div>
    </div>
  </div>
</template>
