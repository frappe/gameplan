<template>
  <Dialog title="Change category title" v-model:open="show">
    <FormControl label="Title" v-model="categoryTitle" autofocus />
    <template #actions>
      <div class="flex justify-end">
        <Button
          variant="solid"
          :disabled="!category"
          @click="handleSubmit"
          :loading="teams.setValue.loading"
        >
          Submit
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Dialog, FormControl, Button } from 'frappe-ui'
import { useDoctype } from 'frappe-ui'
import type { GPTeam } from '@/types/doctypes'
import type { GroupedSpaceItem } from '@/data/groupedSpaces'

const show = ref(false)
const categoryTitle = ref('')
const category = ref<GroupedSpaceItem | null>(null)

const teams = useDoctype<GPTeam>('GP Team')

function openDialog(groupCategory: GroupedSpaceItem) {
  category.value = groupCategory
  categoryTitle.value = groupCategory.title
  show.value = true
}

function handleSubmit() {
  if (category.value) {
    teams.setValue
      .submit({
        name: category.value.name,
        title: categoryTitle.value,
      })
      .then(() => {
        show.value = false
        category.value = null
        categoryTitle.value = ''
      })
  }
}

// Watch for dialog close to reset state
watch(show, (newValue) => {
  if (!newValue) {
    category.value = null
    categoryTitle.value = ''
  }
})

defineExpose({
  openDialog,
})
</script>
