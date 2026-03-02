<script setup lang="ts">
defineProps<{
  /** Number of skeleton rows to render. */
  rows?: number
  /** Number of columns to render per row. */
  cols?: number
}>()
</script>

<template>
  <tr v-for="r in (rows ?? 5)" :key="r">
    <td v-for="c in (cols ?? 4)" :key="c">
      <div class="skeleton h-4 w-full rounded"></div>
    </td>
  </tr>
</template>
