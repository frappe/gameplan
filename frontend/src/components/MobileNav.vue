<template>
  <div class="sm:hidden">
    <Button @click="openModal">
      <div class="flex items-center space-x-2">
        <span> {{ currentPageTitle }} </span>
        <FeatherIcon name="code" class="w-3 rotate-90" />
      </div>
    </Button>
  </div>
  <TransitionRoot appear :show="isOpen" as="template">
    <Dialog as="div" @close="closeModal" class="relative z-10">
      <TransitionChild
        as="template"
        enter="duration-300 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-200 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-black bg-opacity-25" />
      </TransitionChild>

      <div class="fixed inset-0 overflow-y-auto">
        <div class="flex min-h-full items-start justify-center text-center">
          <TransitionChild
            as="template"
            enter="duration-200 ease-out"
            enter-from="opacity-0 -translate-y-full"
            enter-to="opacity-100 translate-y-0"
            leave="duration-200 ease-in"
            leave-from="opacity-100 translate-y-0"
            leave-to="opacity-0 -translate-y-full"
          >
            <DialogPanel
              class="w-full transform overflow-hidden rounded-b-2xl bg-white p-6 text-left align-middle shadow-xl transition-all"
            >
              <div class="mb-2 flex items-center justify-between">
                <DialogTitle
                  as="h3"
                  class="text-lg font-medium leading-6 text-gray-900"
                >
                  Navigation
                </DialogTitle>
                <Button icon="x" appearance="minimal" @click="closeModal" />
              </div>
              <div @click="closeModal">
                <Links
                  :links="navigation"
                  class="flex items-center rounded-md px-2 py-2 font-medium"
                  active="bg-gray-200 text-gray-900"
                  inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                >
                  <template v-slot="{ link }">
                    <div class="flex w-full items-center space-x-2">
                      <span class="grid h-5 w-5 place-items-center">
                        <FeatherIcon :name="link.icon" class="h-4 w-4" />
                      </span>
                      <span class="text-lg">{{ link.name }}</span>
                      <span
                        v-if="
                          link.unreadNotifications &&
                          link.unreadNotifications.data > 0
                        "
                        class="!ml-auto block rounded bg-red-500 px-1 text-sm text-white"
                      >
                        {{ link.unreadNotifications.data }}
                      </span>
                    </div>
                  </template>
                </Links>
                <hr class="my-1 bg-gray-200" />
                <Links
                  :links="teams"
                  class="flex items-center rounded-md px-2 py-2 font-medium"
                  active="bg-gray-200 text-gray-900"
                  inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                >
                  <template v-slot="{ link }">
                    <div class="flex w-full items-center space-x-2">
                      <span
                        class="flex h-5 w-5 items-center justify-center text-xl"
                      >
                        {{ link.icon }}
                      </span>
                      <span class="text-lg">{{ link.name }}</span>
                    </div>
                  </template>
                </Links>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script>
import {
  TransitionRoot,
  TransitionChild,
  Dialog,
  DialogPanel,
  DialogTitle,
} from '@headlessui/vue'
import Links from './Links.vue'
import { teams } from '@/data/teams'
import { unreadNotifications } from '@/data/notifications'

export default {
  name: 'MobileNav',
  components: {
    TransitionRoot,
    TransitionChild,
    Dialog,
    DialogPanel,
    DialogTitle,
    Links,
  },
  data() {
    return {
      isOpen: false,
    }
  },
  methods: {
    openModal() {
      this.isOpen = true
    },
    closeModal() {
      this.isOpen = false
    },
  },
  computed: {
    currentPageTitle() {
      let matchedRoutes = this.$route.matched.map((r) => r.name)
      let title = null
      if (matchedRoutes.includes('TeamPage') && this.$route.params.teamId) {
        title = this.teams.find((t) => t.id === this.$route.params.teamId)?.name
      }
      if (matchedRoutes.includes('PersonProfile')) {
        title = 'People'
      }
      return title || this.$route.name
    },
    teams() {
      return (teams.data || []).map((team) => ({
        name: team.title,
        icon: team.icon,
        route: team.route,
        id: team.name,
      }))
    },
    navigation() {
      return [
        {
          name: 'Home',
          icon: 'home',
          route: {
            name: 'Home',
          },
        },
        {
          name: 'People',
          icon: 'users',
          route: {
            name: 'People',
          },
        },
        {
          name: 'Notifications',
          icon: 'bell',
          route: {
            name: 'Notifications',
          },
          unreadNotifications,
        },
      ]
    },
  },
}
</script>
