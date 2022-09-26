<template>
  <Input
    label="Project Name"
    placeholder="Product Launch"
    @change="
      (project) => $emit('update:modelValue', { ...modelValue, project })
    "
    :value="modelValue.project"
  />
</template>
<script>
export default {
  name: 'OnboardingStepProject',
  props: ['modelValue'],
  emits: ['update:modelValue'],
}
</script>
