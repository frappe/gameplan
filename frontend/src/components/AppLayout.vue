<template>
  <div class="relative flex h-full flex-col" v-if="$users.data.length">
    <div class="h-full flex-1">
      <div class="flex h-full">
        <div class="hidden min-h-0 flex-shrink-0 overflow-auto sm:block">
          <slot name="sidebar" />
        </div>
        <div class="w-full overflow-auto">
          <div class="mx-auto max-w-4xl">
            <slot name="main" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  name: 'AppLayout',
}
</script>
