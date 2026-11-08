<script setup lang="ts">
/**
 * RecurringTimeline — one line per service over the last two years.
 *
 * Each line runs from its first to its last debit; its successive prices are
 * stretches of the same line. A line that probably continues another one
 * under a new label (same exact amount) carries a "link" suggestion, and
 * any two lines can be linked by hand.
 */

import { computed, ref } from 'vue'
import type { RecurringLine, RecurringLinkSuggestion } from '@/api/types'
import { formatAmount } from '@/api/types'
import {
  formatDay,
  formatMonth,
  monthsBefore,
  periodLabel,
  timelinePercent,
} from '@/api/recurring'
import RecurringPicker from '@/components/RecurringPicker.vue'

/** Months shown on the timeline. */
const WINDOW_MONTHS = 24
/** A stretch narrower than this (percent of the width) is drawn at this width. */
const MIN_SEGMENT_WIDTH = 1.2
/** A stretch wider than this (percent) shows its amount inside. */
const LABEL_MIN_WIDTH = 14

const props = defineProps<{
  lines: RecurringLine[]
  suggestions: RecurringLinkSuggestion[]
  today: string
  busy: boolean
}>()

const emit = defineEmits<{
  link: [earlierId: string, laterId: string]
}>()

const linkingId = ref<string | null>(null)

const start = computed(() => monthsBefore(WINDOW_MONTHS, props.today))

// Most recent first: what still runs on top, what stopped long ago at the bottom
const rows = computed(() =>
  [...props.lines].sort(
    (a, b) =>
      (b.last_date ?? '').localeCompare(a.last_date ?? '') || b.monthly_cost - a.monthly_cost,
  ),
)

const byId = computed(() => new Map(props.lines.map((l) => [l.id, l])))

// Suggestion shown on the later line, pointing at the earlier one
const suggestionFor = computed(() => {
  const map = new Map<string, RecurringLine>()
  for (const s of props.suggestions) {
    const earlier = byId.value.get(s.earlier_id)
    if (earlier && byId.value.has(s.later_id)) map.set(s.later_id, earlier)
  }
  return map
})

// One tick every three months, labelled with the month
const ticks = computed(() => {
  const result: { left: number; label: string }[] = []
  const [y0 = 0, m0 = 1] = start.value.split('-').map(Number)
  for (let i = 0; i <= WINDOW_MONTHS; i += 3) {
    const total = y0 * 12 + (m0 - 1) + i
    const iso = `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, '0')}-01`
    if (iso > props.today) break
    result.push({ left: timelinePercent(iso, start.value, props.today), label: formatMonth(iso) })
  }
  return result
})

// Labels near an edge are aligned inwards, so that they are never cut off
function tickAlign(left: number): string {
  if (left < 6) return 'translate-x-0'
  if (left > 94) return '-translate-x-full'
  return '-translate-x-1/2'
}

function bars(line: RecurringLine): { left: number; width: number; amount: number; title: string }[] {
  return line.segments
    .map((s, i) => ({ s, next: line.segments[i + 1] }))
    .filter(({ s }) => s.end >= start.value)
    .map(({ s, next }) => {
      const left = timelinePercent(s.start, start.value, props.today)
      // A price runs until the next price starts: no blank between two prices
      const right = timelinePercent(next ? next.start : s.end, start.value, props.today)
      return {
        left,
        width: Math.max(right - left, MIN_SEGMENT_WIDTH),
        amount: s.amount,
        title: `${formatAmount(s.amount)} · ${s.count} prélèvement${s.count > 1 ? 's' : ''}, du ${formatDay(s.start)} au ${formatDay(s.end)}`,
      }
    })
}

function barClass(line: RecurringLine): string {
  if (!line.running) return 'bg-base-content/25'
  if (line.payment?.kind === 'other' || (!line.payment && line.likely_other)) return 'bg-secondary/60'
  return 'bg-primary'
}

function optionsFor(line: RecurringLine): { id: string; label: string }[] {
  return props.lines
    .filter((l) => l.id !== line.id)
    .map((l) => ({
      id: l.id,
      label: `${l.name} — ${formatAmount(l.amount)} · ${l.first_date ? formatMonth(l.first_date) : '?'} → ${l.last_date ? formatMonth(l.last_date) : '?'}`,
    }))
}

// The line that ends first is the earlier one; the other absorbs it.
function linkWith(line: RecurringLine, otherId: string): void {
  const other = byId.value.get(otherId)
  linkingId.value = null
  if (!other) return
  const lineEnd = line.last_date ?? ''
  const otherEnd = other.last_date ?? ''
  if (otherEnd <= lineEnd) emit('link', other.id, line.id)
  else emit('link', line.id, other.id)
}
</script>

<template>
  <div class="flex flex-col gap-1" data-test="recurring-timeline">
    <!-- Axis -->
    <div class="grid grid-cols-1 sm:grid-cols-[13rem_1fr] gap-3 text-[10px] text-base-content/50">
      <span class="hidden sm:block" />
      <div class="relative h-4">
        <!-- Every other tick on a phone, so that the months do not overlap -->
        <span
          v-for="(t, i) in ticks"
          :key="t.label"
          class="absolute whitespace-nowrap"
          :class="[tickAlign(t.left), { 'hidden sm:inline': i % 2 === 1 }]"
          :style="{ left: `${t.left}%` }"
        >{{ t.label }}</span>
      </div>
    </div>

    <div
      v-for="line in rows"
      :key="line.id"
      class="grid grid-cols-1 sm:grid-cols-[13rem_1fr] gap-x-3 gap-y-1 py-2 border-b border-base-300"
      data-test="timeline-row"
    >
      <div class="min-w-0">
        <p class="text-sm font-medium truncate" :title="line.label ?? line.name">
          {{ line.name }}
        </p>
        <p class="text-xs text-base-content/60">
          {{ formatAmount(line.amount) }} · {{ periodLabel(line.period) }}
          <span v-if="!line.running"> · arrêté</span>
          ·
          <button
            class="link link-hover"
            :disabled="busy"
            @click="linkingId = linkingId === line.id ? null : line.id"
          >relier à…</button>
        </p>
      </div>

      <div class="flex flex-col gap-1 min-w-0">
        <div class="relative h-6 rounded bg-base-200">
          <div
            v-for="(b, i) in bars(line)"
            :key="i"
            class="absolute top-1 bottom-1 rounded-sm text-[10px] leading-4 text-white text-center overflow-hidden whitespace-nowrap"
            :class="barClass(line)"
            :style="{ left: `${b.left}%`, width: `${b.width}%` }"
            :title="b.title"
          >
            <span v-if="b.width >= LABEL_MIN_WIDTH">{{ formatAmount(b.amount) }}</span>
          </div>
        </div>

        <div v-if="suggestionFor.get(line.id)" class="flex flex-wrap items-center gap-2">
          <span class="text-xs text-warning">
            Probablement la suite de « {{ suggestionFor.get(line.id)!.name }} » (même montant)
          </span>
          <button
            class="btn btn-xs btn-warning"
            :disabled="busy"
            @click="emit('link', suggestionFor.get(line.id)!.id, line.id)"
          >Relier</button>
        </div>
        <RecurringPicker
          v-if="linkingId === line.id"
          :options="optionsFor(line)"
          prompt="Même service que :"
          :busy="busy"
          @choose="(id) => linkWith(line, id)"
          @cancel="linkingId = null"
        />
      </div>
    </div>
  </div>
</template>
