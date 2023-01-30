<template>
  <div>
    <header class="sticky top-0 z-10 border-b bg-white py-3 px-4 sm:px-5">
      <div class="flex items-center justify-between">
        <div class="-ml-3">
          <Button
            @click="showCustomiseHomeDialog = true"
            icon-right="chevron-down"
            appearance="minimal"
          >
            <h1 class="text-2xl font-semibold">Home</h1>
          </Button>
        </div>
        <button
          @click="showCommandPalette"
          class="hidden w-full max-w-[20rem] rounded-md focus:outline-none focus:ring focus:ring-gray-300 md:block"
        >
          <Input
            :placeholder="searchPlaceholder"
            icon-left="search"
            class="cursor-pointer"
            :disabled="true"
          />
        </button>
      </div>
    </header>

    <HomeProjects v-if="homePage === 'projects'" />
    <Feed v-if="homePage === 'feed'" />

    <Dialog
      :options="{
        title: 'Home',
      }"
      v-model="showCustomiseHomeDialog"
    >
      <template #body-content>
        <p class="text-base text-gray-600">
          Customise what you see on your homepage
        </p>
        <div class="mt-4 space-y-2">
          <button
            v-for="option in homePageOptions"
            class="flex w-full items-center rounded-md border px-4 py-3"
            :key="option.value"
            @click="homePage = option.value"
            :class="
              homePage == option.value
                ? 'border-blue-500 ring-2 ring-blue-100'
                : 'hover:border-gray-400'
            "
          >
            <CheckCircle
              v-if="homePage == option.value"
              class="mr-2 h-4 w-4 text-blue-500"
            />
            <Circle v-else class="mr-2 h-4 w-4 text-gray-500" />
            <span class="text-base text-gray-900">
              {{ option.label }}
            </span>
          </button>
        </div>
      </template>
    </Dialog>
  </div>
</template>
<script>
import Feed from './Feed.vue'
import HomeProjects from './HomeProjects.vue'
import { showCommandPalette } from '@/components/CommandPalette.vue'
import { getPlatform } from '@/utils'
import { useLocalStorage } from '@/utils/composables'
import CircleDot from '~icons/lucide/circle-dot'
import Circle from '~icons/lucide/circle'
import CheckCircle from '~icons/lucide/check-circle2'

export default {
  name: 'Home',
  components: {
    HomeProjects,
    Feed,
    CircleDot,
    Circle,
    CheckCircle,
  },
  data() {
    return {
      showCustomiseHomeDialog: false,
    }
  },
  setup() {
    // options: projects, feed
    let homePage = useLocalStorage('homePage', 'projects')

    return {
      homePage,
      showCommandPalette,
      homePageOptions: [
        {
          label: 'Pinned, Active & Recent Projects',
          value: 'projects',
        },
        {
          label: 'Discussion feed sorted by most recent',
          value: 'feed',
        },
      ],
    }
  },
  computed: {
    searchPlaceholder() {
      let platform = getPlatform()
      if (platform == 'mac') {
        return 'Jump to project or team (⌘+K)'
      }
      return 'Jump to project or team (Ctrl+K)'
    },
  },
}
</script>
