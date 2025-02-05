<template>
  <node-view-wrapper class="team-task my-2" :class="'team-task-' + task?.name">
    <div class="flex items-center space-x-2">
      <input
        type="checkbox"
        class="h-4 w-4 rounded border-outline-gray-2 text-ink-blue-3 focus:ring-blue-500"
      />
      <input
        class="border-none p-0 [font-size:unset] focus:border-none focus:ring-0"
        v-if="task"
        type="text"
        v-model="$resources.task.doc.title"
      />
    </div>
  </node-view-wrapper>
</template>

<script>
import { NodeViewWrapper, NodeViewContent, nodeViewProps } from '@tiptap/vue-3'

export default {
  components: {
    NodeViewWrapper,
    NodeViewContent,
  },
  props: nodeViewProps,
  resources: {
    task() {
      return {
        type: 'document',
        doctype: 'GP Task',
        name: this.node.attrs.taskId,
      }
    },
  },
  computed: {
    task() {
      return this.$resources.task.doc
    },
  },
}
</script>
