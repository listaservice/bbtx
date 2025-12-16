<script setup lang="ts">
import { onMounted } from "vue";
import { FileSpreadsheet, ExternalLink } from "lucide-vue-next";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();

onMounted(() => {
  userStore.fetchUser();
});
</script>

<template>
  <div
    v-if="userStore.hasGoogleSheets"
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
</template>
