<template>
  <Input
    label="Team Name"
    placeholder="Marketing"
    @change="(team) => $emit('update:modelValue', { ...modelValue, team })"
    :value="modelValue.team"
  />
</template>
<script>
export default {
  name: 'OnboardingStepTeam',
  props: ['modelValue'],
  emits: ['update:modelValue'],
}
</script>
