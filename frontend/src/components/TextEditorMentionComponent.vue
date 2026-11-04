<template>
  <NodeViewWrapper
    as="div"
    class="mention-wrapper inline-block"
    :data-id="node.attrs.id"
    :data-label="node.attrs.label"
    data-type="mention"
  >
    <UserHoverCard :user="node.attrs.id">
      <button
        @click="handleClick"
        class="mention bg-surface-base hover:bg-surface-gray-1 text-ink-gray-8 inline-block"
      >
        @{{ node.attrs.label || node.attrs.id || '' }}
      </button>
    </UserHoverCard>
  </NodeViewWrapper>
</template>

<script setup lang="ts">
import { NodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
import UserHoverCard from './UserHoverCard.vue'
import { useRouter } from 'vue-router'
import { useUser } from '@/data/users'
import { isAnonymousVisitor } from '@/utils/publicAccess'

interface Props extends NodeViewProps {}

const props = defineProps<Props>()
const router = useRouter()

const handleClick = (event: MouseEvent) => {
  event.preventDefault()
  event.stopPropagation()
  if (isAnonymousVisitor()) return

  let user = useUser(props.node.attrs.id)

  if (user.name != '_everyone_') {
    router.push({ name: 'PersonProfileProfile', params: { personId: user.user_profile } })
  }
}
</script>
<style>
.mention-wrapper.ProseMirror-selectednode button {
  background-color: var(--surface-gray-1, #f8f8f8);
}
</style>
