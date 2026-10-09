<template>
  <Dialog :title="`Visibility of ${title}`" v-model:open="show">
    <div class="mt-2 space-y-4">
      <p v-if="!canChange" class="rounded bg-surface-gray-2 px-3 py-2 text-p-sm text-ink-gray-6">
        Only Gameplan Admins can change visibility.
      </p>

      <RadioGroup
        :model-value="selected"
        :disabled="!canChange || saving"
        label="Who can read"
        padded
        @update:model-value="choose($event as Visibility)"
      >
        <Radio
          v-for="tier in tiers"
          :key="tier.value"
          :value="tier.value"
          :label="tier.value + (tier.value === current ? ' (current)' : '')"
          :description="tier.description"
          @click="error && selected === tier.value && choose(tier.value)"
        />
      </RadioGroup>

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
import { Button, Dialog, ErrorMessage, Radio, RadioGroup, toast, useDoctype } from 'frappe-ui'
import { isGameplanAdmin } from '@/data/users'
import {
  VISIBILITY_ANONYMOUS,
  VISIBILITY_DESCRIPTIONS,
  VISIBILITY_TIERS,
  type Visibility,
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
  const lines = [
    i.users_gaining_access &&
      `${countLabel(i.users_gaining_access, 'person', 'people')} will be able to read it.`,
    i.discussions_revealed &&
      `${countLabel(i.discussions_revealed, 'discussion')} ${verb(i.discussions_revealed, 'becomes', 'become')} readable to them, including everything already posted.`,
    i.discussions_made_public &&
      `${countLabel(i.discussions_made_public, 'discussion')} ${verb(i.discussions_made_public, 'becomes', 'become')} readable by anyone on the web, without signing in.`,
    i.users_losing_access &&
      `${countLabel(i.users_losing_access, 'person', 'people')} will lose access${isCommunity.value ? ` across ${countLabel(i.spaces_losing_readers, 'space')}` : ''}, along with their follows and unread markers there.`,
    i.discussions_no_longer_public &&
      `${countLabel(i.discussions_no_longer_public, 'discussion')} ${verb(i.discussions_no_longer_public, 'stops', 'stop')} being readable without signing in.`,
  ].filter((line): line is string => typeof line === 'string')
  if (i.leaving_anonymous) {
    lines.push(
      'Anything that was public may already have been read, cached or indexed elsewhere. Moving it back does not undo that.',
    )
  }
  if (isCommunity.value && selected.value === VISIBILITY_ANONYMOUS) {
    lines.push(
      'Spaces already set to Anonymous become public too. General and Member Access spaces stay restricted.',
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
function countLabel(n: number, one: string, many = `${one}s`) {
  return `${n} ${n === 1 ? one : many}`
}
</script>
