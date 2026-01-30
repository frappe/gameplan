<template>
  <Dialog :options="{ title, size: '3xl' }" v-model="showDialog">
    <template #body-content>
      <div class="mb-2 flex items-center text-base" v-if="currentRevision">
        <UserInfo :email="currentRevision.owner" v-slot="{ user }">
          <UserProfileLink class="mr-3" :user="user.name">
            <UserAvatar :user="user.name" />
          </UserProfileLink>
          <div>
            <UserProfileLink
              class="font-medium text-ink-gray-8 hover:text-ink-blue-4"
              :user="user.name"
            >
              {{ user.full_name }}
            </UserProfileLink>
            <time
              class="block text-ink-gray-5"
              :datetime="currentRevision.creation"
              :title="dayjsLocal(currentRevision.creation)"
            >
              {{ dayjsLocal(currentRevision.creation).format('LLL') }}
            </time>
          </div>
        </UserInfo>
      </div>
      <div
        v-if="currentRevision"
        v-html="htmlDiff"
        class="ProseMirror prose prose-sm rounded-md prose-p:my-1 prose-table:table-fixed prose-th:relative prose-th:border prose-th:border-outline-gray-2 prose-th:bg-surface-gray-2 prose-th:p-2 prose-td:relative prose-td:border prose-td:border-outline-gray-2 prose-td:p-2"
      />
    </template>
    <template v-if="currentRevision && (hasNext || hasPrevious)" #actions>
      <div class="flex w-full justify-between">
        <div>
          <Button @click="previous" v-if="hasPrevious"> Previous </Button>
        </div>
        <Button @click="next" v-if="hasNext">Next</Button>
      </div>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { dayjsLocal, useCall } from 'frappe-ui'
import HtmlDiff from 'htmldiff-js'
import UserProfileLink from './UserProfileLink.vue'

interface Revision {
  owner: string
  creation: string
  old_value: string
  new_value: string
}

interface Props {
  modelValue: boolean
  doctype: string
  name: string | number
  fieldname: string
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()

const currentRevisionIndex = ref(0)
const showDialog = computed({
  get() {
    return props.modelValue
  },
  set(value: boolean) {
    emit('update:modelValue', value)
  },
})

const revisionUrl = computed(() => `/api/v2/document/${props.doctype}/${props.name}/method/get_revisions`)
const revisions = useCall<Revision[], { fieldname: string }>({
  url: revisionUrl,
  immediate: false,
})

watch(
  () => showDialog.value,
  (value) => {
    if (value) {
      currentRevisionIndex.value = 0
      revisions.submit({ fieldname: props.fieldname })
    }
  },
  { immediate: true },
)

function previous() {
  const maxIndex = Math.max((revisions.data?.length ?? 0) - 1, 0)
  let index = currentRevisionIndex.value + 1
  if (index > maxIndex) {
    index = maxIndex
  }
  currentRevisionIndex.value = index
}

function next() {
  let index = currentRevisionIndex.value - 1
  if (index < 0) {
    index = 0
  }
  currentRevisionIndex.value = index
}

const title = computed(() => {
  if (revisions.data) {
    if (revisions.data.length === 0) return 'No Revisions'
    if (revisions.data.length === 1) return '1 Revision'
    return `${revisions.data.length} Revisions`
  }
  return 'Loading...'
})

const currentRevision = computed(() => {
  if (!revisions.data) {
    return null
  }
  return revisions.data[currentRevisionIndex.value]
})

const hasPrevious = computed(() => {
  if (!currentRevision.value || !revisions.data) return false
  return currentRevisionIndex.value < revisions.data.length - 1
})

const hasNext = computed(() => {
  if (!currentRevision.value) return false
  return currentRevisionIndex.value > 0
})

const htmlDiff = computed(() => {
  if (!currentRevision.value) {
    return null
  }

  const oldHtml = currentRevision.value.old_value
  const newHtml = currentRevision.value.new_value

  // because of commonjs and esm shenanigans
  const makeDiff = HtmlDiff.default?.execute || HtmlDiff.execute
  return makeDiff(oldHtml, newHtml)
})
</script>
<style>
ins {
  all: unset;
  background-color: theme('colors.green.100');
}
del {
  all: unset;
  background-color: theme('colors.red.100');
}
</style>
