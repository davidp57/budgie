<script setup lang="ts">
/**
 * DonutChart — Renders a Chart.js doughnut chart on a canvas.
 *
 * Props:
 *   labels     — slice labels
 *   data       — slice values (absolute numbers; negative values are made positive)
 *   title      — chart title shown in the center legend
 *   total      — optional pre-computed total (centimes); displayed below title
 *   activeLabel — currently highlighted label (drives visual selection)
 *
 * Emits:
 *   slice-click({ label, index }) — user clicked a slice
 */

import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Chart, ArcElement, DoughnutController, Legend, Tooltip } from 'chart.js'
import type { ChartEvent, ActiveElement } from 'chart.js'
import { formatAmount } from '@/api/types'

Chart.register(ArcElement, DoughnutController, Legend, Tooltip)

const props = defineProps<{
  labels: string[]
  data: number[]
  title: string
  total: number
  activeLabel?: string | null
}>()

const emit = defineEmits<{
  'slice-click': [payload: { label: string; index: number }]
}>()

// ── Palette ────────────────────────────────────────────────────────
const COLORS = [
  '#6366f1', '#f59e0b', '#10b981', '#ef4444', '#3b82f6',
  '#8b5cf6', '#f97316', '#14b8a6', '#ec4899', '#84cc16',
  '#06b6d4', '#a855f7', '#f43f5e', '#22c55e', '#eab308',
]

function palette(n: number): string[] {
  return Array.from({ length: n }, (_, i) => COLORS[i % COLORS.length]!)
}

// ── Canvas ref & Chart instance ────────────────────────────────────
const canvasRef = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null

function buildChart(): void {
  if (!canvasRef.value) return
  if (chart) {
    chart.destroy()
    chart = null
  }

  const absData = props.data.map((v) => Math.abs(v))
  const colors = palette(props.labels.length)

  // Highlight active slice with a thicker border if active
  const borderWidths = props.labels.map((lbl) =>
    props.activeLabel && props.activeLabel === lbl ? 3 : 1,
  )
  const borderColors = props.labels.map((lbl) =>
    props.activeLabel && props.activeLabel === lbl ? '#1d4ed8' : '#fff',
  )

  chart = new Chart(canvasRef.value, {
    type: 'doughnut',
    data: {
      labels: props.labels,
      datasets: [
        {
          data: absData,
          backgroundColor: colors,
          borderWidth: borderWidths,
          borderColor: borderColors,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '60%',
      onClick(_event: ChartEvent, elements: ActiveElement[]) {
        const el = elements[0]
        if (!el) return
        const idx = el.index
        const label = props.labels[idx] ?? ''
        emit('slice-click', { label, index: idx })
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 12,
            font: { size: 11 },
          },
        },
        tooltip: {
          callbacks: {
            label(ctx) {
              const raw = ctx.parsed as number
              return ` ${ctx.label}: ${formatAmount(-raw)}`
            },
          },
        },
      },
    },
  })
}

onMounted(buildChart)
watch(() => [props.labels, props.data, props.activeLabel], buildChart, { deep: true })
onBeforeUnmount(() => {
  chart?.destroy()
  chart = null
})
</script>

<template>
  <div class="flex flex-col items-center">
    <p class="text-sm font-semibold mb-1 text-center">{{ title }}</p>
    <p class="text-xs text-base-content/60 mb-2 tabular-nums">{{ formatAmount(total) }}</p>
    <canvas ref="canvasRef" class="max-w-[220px] cursor-pointer" />
  </div>
</template>
