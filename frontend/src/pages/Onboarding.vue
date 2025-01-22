<template>
  <div class="flex">
    <div class="bg-surface-menu-bar min-w-[256px] pointer-events-none min-h-screen">
      <div class="p-2">
        <UserDropdown />
      </div>
      <div class="flex-1">
        <nav class="space-y-0.5 px-2">
          <div
            v-for="link in navigation"
            :key="link.name"
            class="flex items-center rounded px-2 py-1 text-ink-gray-8 transition"
            activeClass="bg-surface-selected shadow-sm"
            inactiveClass="hover:bg-surface-gray-2"
          >
            <div class="flex w-full items-center space-x-2">
              <span class="grid h-5 w-6 place-items-center">
                <component :is="link.icon" class="h-4 w-4 text-ink-gray-7" />
              </span>
              <span class="text-sm">{{ link.name }}</span>
            </div>
          </div>
        </nav>
        <div class="mt-6 px-2">
          <div
            class="flex h-7 w-full items-center justify-between group px-2 py-1.5 rounded hover:bg-surface-gray-2"
          >
            <h3 class="text-sm text-ink-gray-5">Spaces</h3>
          </div>
          <div class="mb-2 mt-0.5 space-y-0.5">
            <div class="flex h-7 items-center rounded px-2 text-ink-gray-8 transition">
              <span class="inline-flex min-w-0 items-center space-x-2">
                <span class="flex-shrink-0 flex h-5 w-6 items-center justify-center text-xl">
                  {{ space.icon }}
                </span>
                <span class="truncate text-sm flex-grow">
                  {{ space.title }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="max-w-4xl mx-auto px-4 pt-14">
      <div class="max-w-xl mx-auto">
        <div class="text-2xl font-semibold text-ink-gray-9">Welcome to Gameplan</div>

        <div class="mt-2 pt-8 border-t">
          <h2 class="text-base font-medium text-ink-gray-9 mb-2">Let's create your first space</h2>
          <p class="text-p-sm text-ink-gray-7">
            A space is where your discussions live. Create one for your team, project, or any topic
            you want to discuss and organize.
          </p>
          <div class="mt-6 space-y-2">
            <div class="space-x-2 flex items-start w-full">
              <IconPicker v-model="space.icon" v-slot="{ isOpen }">
                <Button>
                  <template #icon>
                    <span v-if="space.icon">{{ space.icon }}</span>
                    <LucidePlus v-else class="h-4 w-4" />
                  </template>
                </Button>
              </IconPicker>
              <div class="w-full">
                <FormControl
                  type="text"
                  class="w-full"
                  placeholder="Townhall, Engineering, Project X"
                  id="new-space-name"
                  :modelValue="space.title"
                  @update:modelValue="
                    (value) => (space.title = value.length <= 50 ? value : value.slice(0, 50))
                  "
                  maxlength="50"
                  autocomplete="off"
                  description="Give your space a short and descriptive name"
                >
                  <template #suffix>
                    <span class="text-ink-gray-5 text-sm">
                      {{ 50 - space.title.length }}
                    </span>
                  </template>
                </FormControl>
              </div>
            </div>
          </div>
        </div>
        <div class="mt-8 border-t pt-8">
          <h3 class="text-base font-medium text-ink-gray-9 mb-2">Invite team members</h3>
          <p class="text-sm text-ink-gray-7">
            Add email addresses of people you'd like to invite to this space
          </p>
          <div class="mt-3">
            <FormControl
              type="textarea"
              v-model="emailInput"
              placeholder="jane@example.com, mary@example.com, ..."
              :rows="3"
              class="w-full"
              @blur="validateEmails(emailInput)"
              description="Separate multiple email addresses with commas or new lines"
            />
            <p v-if="emailError" class="text-xs text-red-600 mt-1">
              {{ emailError }}
            </p>
          </div>
        </div>
        <div class="mt-4">
          <ErrorMessage :message="onboarding.error" />
        </div>
        <div class="mt-8 flex justify-end">
          <Button
            variant="solid"
            :loading="onboarding.loading"
            :disabled="!space.title"
            @click="submit"
          >
            Continue
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCall } from 'frappe-ui/src/data-fetching'
import UserDropdown from '@/components/UserDropdown.vue'
import { joinedSpaces, spaces } from '@/data/spaces'
import { teams } from '@/data/teams'

import LucideFiles from '~icons/lucide/files'
import LucideInbox from '~icons/lucide/inbox'
import LucideListTodo from '~icons/lucide/list-todo'
import LucideNewspaper from '~icons/lucide/newspaper'
import LucidePlus from '~icons/lucide/plus'
import LucideUsers2 from '~icons/lucide/users-2'
import LucideSearch from '~icons/lucide/search'

const space = reactive({
  title: '',
  icon: '',
})
const emailInput = ref('')
const emailError = ref('')

const router = useRouter()

const validateEmails = (emails: string) => {
  const emailList = emails
    .split(/[\n,]/)
    .map((e) => e.trim())
    .filter((e) => e)
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const invalidEmails = emailList.filter((email) => !emailRegex.test(email.trim()))
  if (invalidEmails.length) {
    emailError.value = `Invalid email(s): ${invalidEmails.join(', ')}`
    return false
  }
  emailError.value = ''
  return true
}

type OnboardingParams = {
  space: string
  icon: string
  emails: string[]
}

const onboarding = useCall<string, OnboardingParams>({
  url: '/api/v2/method/gameplan.api.onboarding',
  method: 'POST',
  immediate: false,
  beforeSubmit() {
    if (!space.title) {
      throw new Error('Please enter a space name')
    }
  },
  onSuccess(spaceId) {
    teams.reload()
    spaces.reload()
    joinedSpaces.reload()

    router.replace({ name: 'Space', params: { spaceId } })
  },
})

function submit() {
  onboarding.submit({
    space: space.title,
    icon: space.icon,
    emails: emailInput.value.split(/[\n,]/),
  })
}

const navigation = [
  {
    name: 'Home',
    icon: LucideNewspaper,
  },
  {
    name: 'Inbox',
    icon: LucideInbox,
  },
  {
    name: 'Tasks',
    icon: LucideListTodo,
  },
  {
    name: 'Pages',
    icon: LucideFiles,
  },
  {
    name: 'People',
    icon: LucideUsers2,
  },
  {
    name: 'Search',
    icon: LucideSearch,
  },
]
</script>
