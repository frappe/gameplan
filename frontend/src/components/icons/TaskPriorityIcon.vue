<template>
  <div class="grid place-items-center">
    <div
      class="h-3 w-3 rounded-full"
      :class="{
        'bg-surface-red-5': priority === 'High',
        'bg-surface-amber-5': priority === 'Medium',
        'bg-surface-gray-5': priority === 'Low',
      }"
    ></div>
  </div>
</template>
<script>
export default {
  name: 'TaskPriorityIcon',
  props: {
    priority: {
      type: String,
      required: true,
    },
  },
}
</script>
