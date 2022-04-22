<template>
  <node-view-wrapper
    class="my-2 team-task"
    :class="'team-task-' + task?.name"
  >
    <div class="flex items-center space-x-2">
      <input
        type="checkbox"
        class="w-4 h-4 text-blue-500 border-gray-300 rounded focus:ring-blue-500"
      />
      <input
        class="p-0 border-none [font-size:unset] focus:border-none focus:ring-0"
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
        doctype: 'Team Task',
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
