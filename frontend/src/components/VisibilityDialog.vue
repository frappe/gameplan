<template>
  <Dialog :title="`Visibility of ${title}`" v-model:open="show">
    <div class="mt-2 space-y-4">
      <p v-if="!canChange" class="rounded bg-surface-gray-2 px-3 py-2 text-p-sm text-ink-gray-6">
        Only Gameplan Admins can change visibility.
      </p>

      <div class="space-y-2" role="radiogroup" :aria-label="`Visibility of ${title}`">
        <button
          v-for="tier in tiers"
          :key="tier.value"
          type="button"
          role="radio"
          :aria-checked="selected === tier.value"
          :disabled="!canChange || saving"
          class="flex w-full items-start gap-3 rounded border px-3 py-2.5 text-left disabled:cursor-not-allowed"
          :class="
            selected === tier.value
              ? 'border-outline-gray-4 bg-surface-gray-2'
              : 'border-outline-gray-2 hover:bg-surface-gray-1'
          "
          @click="choose(tier.value)"
        >
          <span :class="[visibilityIcon(tier.value), 'mt-0.5 size-4 shrink-0 text-ink-gray-6']" />
          <span class="min-w-0">
            <span class="block text-base-medium text-ink-gray-8">
              {{ tier.value }}
              <span v-if="tier.value === current" class="text-sm text-ink-gray-5"> (current)</span>
            </span>
            <span class="block text-p-sm text-ink-gray-5">{{ tier.description }}</span>
          </span>
        </button>
      </div>

      <div v-if="changing" class="space-y-1.5 rounded border border-outline-gray-2 px-3 py-2.5">
        <div class="text-base-medium text-ink-gray-8">What this changes</div>
        <div v-if="impactLoading" class="text-p-sm text-ink-gray-5">Working it out…</div>
        <ul v-else class="list-disc space-y-1 pl-4 text-p-sm text-ink-gray-7">
          <li v-for="line in impactLines" :key="line">{{ line }}</li>
        </ul>
      </div>

      <ErrorMessage :message="error" />
    </div>

    <template #actions>
      <div class="flex justify-end gap-2">
        <Button @click="show = false">Cancel</Button>
        <Button
          variant="solid"
          :disabled="!canChange || !changing || impactLoading || previewedTier !== selected"
          :loading="saving"
          @click="save"
        >
          Change visibility
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, toast, useDoctype } from 'frappe-ui'
import { isGameplanAdmin } from '@/data/users'
import {
  VISIBILITY_ANONYMOUS,
  VISIBILITY_DESCRIPTIONS,
  VISIBILITY_TIERS,
  type Visibility,
  visibilityIcon,
  visibilityTier,
} from '@/utils/visibility'

interface Impact {
  users_gaining_access: number
  users_losing_access: number
  discussions_revealed: number
  discussions_made_public: number
  discussions_no_longer_public: number
  spaces_losing_readers: number
  leaving_anonymous: boolean
}

const props = defineProps<{
  doctype: 'GP Team' | 'GP Project'
  name: string
  title: string
  visibility?: string | null
}>()
const emit = defineEmits<{ (event: 'changed', visibility: Visibility): void }>()
const show = defineModel<boolean>()

const isCommunity = computed(() => props.doctype === 'GP Team')
const tiers = computed(() =>
  VISIBILITY_TIERS.map((value) => ({
    value,
    description:
      value === VISIBILITY_ANONYMOUS
        ? isCommunity.value
          ? 'Anyone with the link can read the community. Each space inside chooses for itself.'
          : 'Anyone with the link, no account needed, if its community is Anonymous too.'
        : VISIBILITY_DESCRIPTIONS[value] + '.',
  })),
)

const documents = useDoctype(props.doctype)
const canChange = computed(() => isGameplanAdmin())
const current = computed(() => visibilityTier(props.visibility))
const selected = ref<Visibility>(current.value)
const changing = computed(() => selected.value !== current.value)
const impact = ref<Impact | null>(null)
const previewedTier = ref<Visibility | null>(null)
let previewVersion = 0
const impactLoading = ref(false)
const saving = ref(false)
const error = ref('')

watch([show, () => props.name], () => {
  previewVersion++
  selected.value = current.value
  impact.value = null
  previewedTier.value = null
  impactLoading.value = false
  error.value = ''
})

async function choose(tier: Visibility) {
  if (!canChange.value || saving.value) return
  const version = ++previewVersion
  selected.value = tier
  impact.value = null
  previewedTier.value = null
  impactLoading.value = false
  error.value = ''
  if (!changing.value) return
  impactLoading.value = true
  try {
    const result = (await documents.runDocMethod.submit({
      name: props.name,
      method: 'get_visibility_change_impact',
      params: { visibility: tier },
    })) as unknown as Impact
    if (version !== previewVersion || !show.value) return
    if (!result) throw new Error('Could not work out what this changes')
    impact.value = result
    previewedTier.value = tier
  } catch (e) {
    if (version !== previewVersion) return
    error.value = (e as Error).message || 'Could not work out what this changes'
  } finally {
    if (version === previewVersion) impactLoading.value = false
  }
}

const impactLines = computed(() => {
  const i = impact.value
  if (!i) return []
  const lines: string[] = []
  if (i.users_gaining_access) {
    lines.push(`${people(i.users_gaining_access)} will be able to read it.`)
  }
  if (i.discussions_revealed) {
    lines.push(
      `${discussions(i.discussions_revealed)} ${verb(i.discussions_revealed, 'becomes', 'become')} readable to them, including everything already posted.`,
    )
  }
  if (i.discussions_made_public) {
    lines.push(
      `${discussions(i.discussions_made_public)} ${verb(i.discussions_made_public, 'becomes', 'become')} readable by anyone on the web, without signing in.`,
    )
  }
  if (i.users_losing_access) {
    const where = isCommunity.value ? ` across ${spaces(i.spaces_losing_readers)}` : ''
    lines.push(
      `${people(i.users_losing_access)} will lose access${where}, along with their follows and unread markers there.`,
    )
  }
  if (i.discussions_no_longer_public) {
    lines.push(
      `${discussions(i.discussions_no_longer_public)} ${verb(i.discussions_no_longer_public, 'stops', 'stop')} being readable without signing in.`,
    )
  }
  if (i.leaving_anonymous) {
    lines.push(
      'Anything that was public may already have been read, cached or indexed elsewhere. Moving it back does not undo that.',
    )
  }
  if (isCommunity.value && selected.value === VISIBILITY_ANONYMOUS) {
    lines.push(
      'No space inside becomes public from this. Each space needs its own Anonymous setting.',
    )
  }
  if (!lines.length) lines.push('Nobody gains or loses access.')
  return lines
})

async function save() {
  if (
    !canChange.value ||
    !changing.value ||
    saving.value ||
    impactLoading.value ||
    previewedTier.value !== selected.value
  )
    return
  const tier = selected.value
  saving.value = true
  error.value = ''
  try {
    await documents.runDocMethod.submit({
      name: props.name,
      method: 'set_visibility',
      params: { visibility: tier },
    })
    emit('changed', tier)
    toast.success(`${props.title} is now ${tier}`)
    show.value = false
  } catch (e) {
    error.value = (e as Error).message || 'Could not change visibility'
  } finally {
    saving.value = false
  }
}

function verb(n: number, one: string, many: string) {
  return n === 1 ? one : many
}
function people(n: number) {
  return n === 1 ? '1 person' : `${n} people`
}
function discussions(n: number) {
  return n === 1 ? '1 discussion' : `${n} discussions`
}
function spaces(n: number) {
  return n === 1 ? '1 space' : `${n} spaces`
}
</script>
