<template>
  <GPEditor
    :extensions="extensions"
    :content="content"
    :editable="false"
    editor-class="prose-v3 max-w-none relative"
  />
</template>

<script setup lang="ts">
import GPEditor from '@/components/editor/GPEditor.vue'
import { commentExtensions } from '@/components/editor/commentExtensions'

// A post body, read-only, rendered by the same editor schema the app uses so mentions,
// quotes, embeds and collapsible sections look the way they do for members. No quote
// controller: there is nothing to reply to without signing in.
defineProps<{ content?: string | null }>()

const extensions = commentExtensions()
</script>
