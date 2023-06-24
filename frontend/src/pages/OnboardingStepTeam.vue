<template>
  <FormControl
    label="Team Name"
    placeholder="Marketing"
    @update:modelValue="
      (team) => $emit('update:modelValue', { ...modelValue, team })
    "
    v-model="modelValue.team"
  />
</template>
<script>
export default {
  name: 'OnboardingStepTeam',
  props: ['modelValue'],
  emits: ['update:modelValue'],
}
</script>
