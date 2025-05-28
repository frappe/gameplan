<template>
  <NodeViewWrapper
    class="relative mt-2 first:mt-0 border-l-[6px] hover:border-outline-gray-2 transition-colors overflow-hidden"
    :data-rich-quote-id="node.attrs.quoteId"
  >
    <button
      class="absolute inset-0 transition-colors dark:hover:bg-[rgba(255,255,255,0.1)] hover:bg-[rgba(0,0,0,0.02)]"
      @click="handleClick"
    ></button>
    <div class="flex items-center gap-2 p-2 not-prose">
      <UserAvatar size="xs" :user="node.attrs.author" />
      <div class="text-xs">{{ useUser(node.attrs.author).full_name.trim() }}:</div>
    </div>
    <NodeViewContent class="px-2 py-0" />
  </NodeViewWrapper>
</template>
<script setup lang="ts">
import { NodeViewWrapper, NodeViewContent, nodeViewProps } from '@tiptap/vue-3'
import UserAvatar from '../UserAvatar.vue'
import { useUser } from '@/data/users'
import { DOMSerializer } from '@tiptap/pm/model'

const props = defineProps(nodeViewProps)

function setSelectionToEnd() {
  if (props.editor && props.editor.isEditable && props.getPos && props.node) {
    const endPos = props.getPos() + props.node.nodeSize
    props.editor.commands.setTextSelection(endPos)
    props.editor.commands.focus()
  }
}

function handleClick() {
  if (props.editor && !props.editor.isEditable && props.extension.options.onClick) {
    const schema = props.editor.schema
    const serializer = DOMSerializer.fromSchema(schema)
    const div = document.createElement('div')
    div.appendChild(serializer.serializeFragment(props.node.content, { document }))
    const htmlContent = div.innerHTML

    props.extension.options.onClick({
      quoteId: props.node.attrs.quoteId,
      author: props.node.attrs.author,
      content: htmlContent,
    })
  } else {
    setSelectionToEnd()
  }
}
</script>
