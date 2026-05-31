<template>
  <Teleport defer to="[data-space-header-actions]">
    <div class="flex items-center gap-2">
      <slot />
    </div>
  </Teleport>
</template>
