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
  <div v-if="userStore.hasGoogleSheets" class="space-y-3">
    <!-- Avertizare Securitate -->
    <div
      class="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start space-x-3"
    >
      <AlertTriangle class="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
      <div class="flex-1">
        <p class="text-sm font-semibold text-red-800">
          ⚠️ IMPORTANT - Securitate
        </p>
        <p class="text-xs text-red-700 mt-1">
          NU partaja link-ul Google Sheets cu nimeni! Oricine are link-ul poate
          vedea și șterge toate echipele și datele tale.
        </p>
      </div>
    </div>

    <!-- Google Sheets Link -->
    <div
      class="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center justify-between"
    >
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
  </div>
</template>
