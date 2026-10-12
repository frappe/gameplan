<template>
  <ReactionsUI
    :reactionsCount="reactionsCount"
    :toggleReaction="toggleReaction"
    :toolTipText="toolTipText"
    :standardEmojis="standardEmojis"
    :readOnlyMode="readOnly"
  />
</template>
<script setup>
import { defineAsyncComponent, computed } from 'vue'
import { useReactions } from '@/data/reactions'
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
const props = defineProps(['reactions', 'doctype', 'name', 'readOnlyMode'])
const readOnly = computed(() => Boolean(props.readOnlyMode) || isAnonymousVisitor())
const emit = defineEmits(['update:reactions'])

const { reactionsCount, toggleReaction, toolTipText, standardEmojis } = useReactions({
  reactions: () => props.reactions,
  doctype: () => props.doctype,
  name: () => props.name,
  readOnlyMode: readOnly,
  onUpdate: (reactions) => emit('update:reactions', reactions),
})
</script>
