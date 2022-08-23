<template>
  <div class="relative flex flex-col" v-if="$users.data.length">
    <div class="sticky top-0 z-10 bg-white border-b">
      <div class="px-4 lg:container lg:px-0">
        <slot name="navbar" />
      </div>
    </div>
    <div class="flex-1 h-full px-4 lg:container lg:px-0">
      <div class="flex h-full">
        <div class="flex-shrink-0 hidden w-64 min-h-0 pb-40 sm:block">
          <slot name="sidebar" />
        </div>
        <div class="hidden w-16 h-full sm:block shrink-0"></div>
        <div class="w-full">
          <slot name="main" />
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
