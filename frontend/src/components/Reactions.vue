<template>
  <ReactionsUI
    :reactionsCount="reactionsCount"
    :toggleReaction="toggleReaction"
    :toolTipText="toolTipText"
    :standardEmojis="standardEmojis"
    :readOnlyMode="readOnly"
  />
</template>
<script setup lang="ts">
import { defineAsyncComponent, computed } from 'vue'
import { useReactions, type ReactableDoctype } from '@/data/reactions'
import { useIsMobile } from '@/utils/useIsMobile'
import { isAnonymousVisitor } from '@/utils/publicAccess'

const isMobileViewport = useIsMobile()
const ReactionsMobile = defineAsyncComponent(() => import('./ReactionsMobile.vue'))
const ReactionsDesktop = defineAsyncComponent(() => import('./ReactionsDesktop.vue'))
const ReactionsUI = computed(() => {
  if (isMobileViewport.value) {
    return ReactionsMobile
  } else {
    return ReactionsDesktop
  }
})
const props = defineProps<{
  doctype: ReactableDoctype
  name: string | number
  readOnlyMode?: boolean
}>()
const readOnly = computed(() => Boolean(props.readOnlyMode) || isAnonymousVisitor())

const { reactionsCount, toggleReaction, toolTipText, standardEmojis } = useReactions({
  doctype: () => props.doctype,
  name: () => props.name,
  readOnlyMode: readOnly,
})
</script>
