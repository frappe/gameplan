<template>
  <div v-if="profile">
    <PageHeader>
      <Breadcrumbs
        :items="[
          { label: 'People', route: { name: 'People' } },
          {
            label: profile?.full_name,
            route: { name: 'PersonProfile', params: { personId } },
          },
        ]"
      />
      <div class="h-7"></div>
    </PageHeader>
    <div>
      <CoverImage
        :imageUrl="profile.cover_image"
        :imagePosition="profile.cover_image_position"
        :editable="$isSessionUser(profile.user)"
        @change="
          ({ imageUrl, imagePosition }) => {
            $resources.profile.setValue.submit({
              cover_image: imageUrl,
              cover_image_position: imagePosition,
            })
          }
        "
      />
    </div>
    <div class="-mt-4 body-container">
      <div class="flex items-center">
        <div class="-mx-1 inline-flex translate-y-0">
          <ImagePreview v-model:show="imagePreview.show" :imageUrl="imagePreview.imageUrl" />
          <button
            v-if="currentUser.user_image"
            @click="
              () => {
                imagePreview.imageUrl = currentUser.user_image
                imagePreview.show = true
              }
            "
            class="rounded-full shrink-0 bg-surface-white outline-none hover:brightness-110 focus-visible:ring focus-visible:ring-outline-gray-3"
          >
            <UserImage
              class="h-[100px] w-[100px] rounded-full border-4 border-outline-white object-cover"
              :user="currentUser.name"
            />
          </button>
          <button
            v-else
            @click="editDialog.show = true"
            class="h-32 w-32 rounded-full border-4 border-white bg-surface-gray-3 text-sm text-ink-gray-5"
            :class="{ 'hover:bg-surface-gray-4': $isSessionUser(profile.user) }"
            :disabled="!$isSessionUser(profile.user)"
          >
            <span v-if="$isSessionUser(profile.user)"> Upload Image </span>
          </button>
        </div>
        <div class="ml-6 flex-1">
          <h2 class="mt-2 text-3xl font-semibold text-ink-gray-8">
            {{ user ? user.full_name : profile.full_name }}
          </h2>
          <p v-if="profile.bio" class="mt-2 text-base text-ink-gray-6">
            {{ profile.bio }}
          </p>
        </div>
        <div v-if="$isSessionUser(profile.user)">
          <Button icon-left="lucide-edit" @click="editDialog.show = true" class="hidden sm:flex">
            Edit Profile
          </Button>
          <Button
            label="Edit Profile"
            icon="lucide-edit"
            @click="editDialog.show = true"
            class="sm:hidden"
          />
        </div>
      </div>

      <div class="mb-4 mt-6">
        <TabButtons
          class="inline-block"
          :buttons="
            [
              { label: 'About' },
              { label: 'Posts' },
              { label: 'Replies' },
              $isSessionUser(profile.user) ? { label: 'Bookmarks' } : null,
            ].filter(Boolean)
          "
          v-model="activeTab"
        />
      </div>

      <router-view :profile="$resources.profile" />
    </div>
    <Dialog
      v-if="$isSessionUser(profile.user)"
      title="Edit Profile"
      v-model:open="editDialog.show"
      @after-leave="discard"
    >
      <div class="space-y-4">
        <ProfileImageEditor :profile="$resources.profile" v-if="editDialog.editingProfilePhoto" />
        <template v-else>
          <div class="flex items-center gap-4">
            <UserAvatar size="lg" :user="profile.user" />
            <Button @click="editDialog.editingProfilePhoto = true"> Edit Profile Photo </Button>
          </div>
          <FormControl label="First Name" v-model="user.first_name" />
          <FormControl label="Last Name" v-model="user.last_name" />
          <FormControl label="Bio" v-model="profile.bio" type="textarea" maxlength="280" />
        </template>
      </div>
      <template #actions>
        <Button
          variant="solid"
          class="w-full"
          @click="save"
          :loading="$resources.user.setValue.loading || $resources.profile.setValue.loading"
        >
          Save
        </Button>
      </template>
    </Dialog>
  </div>
</template>
<script>
import { Breadcrumbs, Dialog, FileUploader, FormControl, TabButtons } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import CoverImage from '@/components/CoverImage.vue'
import ImagePreview from '../components/ImagePreview.vue'
import ColorPicker from '@/components/ColorPicker.vue'
import ProfileImageEditor from '@/components/ProfileImageEditor.vue'
import UserImage from '@/components/UserImage.vue'
import { isSessionUser } from '@/data/session'

export default {
  name: 'PersonProfile',
  props: ['personId'],
  components: {
    CoverImage,
    Dialog,
    FileUploader,
    ImagePreview,
    ColorPicker,
    ProfileImageEditor,
    UserImage,
    FormControl,
    TabButtons,
    Breadcrumbs,
    PageHeader,
  },
  data() {
    return {
      editing: false,
      editDialog: { show: false, editingProfilePhoto: false },
      profilePhotoDialog: { show: false },
      imagePreview: { show: false, imageUrl: null },
    }
  },
  resources: {
    profile() {
      return {
        type: 'document',
        doctype: 'GP User Profile',
        name: this.personId,
        realtime: true,
        whitelistedMethods: {
          setImage: 'set_image',
          removeImageBackground: 'remove_image_background',
          revertImageBackground: 'revert_image_background',
          isBackgroundRemovalAvailable: 'is_background_removal_available',
        },
      }
    },
    user() {
      if (!this.profile || !this.$isSessionUser(this.profile.user)) return
      return {
        type: 'document',
        doctype: 'User',
        name: this.profile.user,
        realtime: true,
      }
    },
  },
  computed: {
    profile() {
      return this.$resources.profile.doc
    },
    user() {
      return this.$resources.user?.doc
    },
    currentUser() {
      return this.$user(this.profile.user)
    },
    activeTab: {
      get() {
        return {
          PersonProfileAboutMe: 'About',
          PersonProfilePosts: 'Posts',
          PersonProfileReplies: 'Replies',
          PersonProfileBookmarks: 'Bookmarks',
        }[this.$route.name]
      },
      set(value) {
        let route = {
          About: { name: 'PersonProfileAboutMe' },
          Posts: { name: 'PersonProfilePosts' },
          Replies: { name: 'PersonProfileReplies' },
          Bookmarks: { name: 'PersonProfileBookmarks' },
        }[value]
        if (route) {
          this.$router.push(route)
        }
      },
    },
  },
  methods: {
    save() {
      this.$resources.user.setValue
        .submit({
          first_name: this.user.first_name,
          last_name: this.user.last_name,
        })
        .then(() => {
          this.$resources.profile.setValue.submit({
            bio: this.profile.bio,
          })
          this.editDialog.show = false
        })
    },
    discard() {
      this.$resources.user.reload()
      this.$resources.profile.reload()
      this.editDialog = this.$options.data().editDialog
    },
    setUserImage(url) {
      this.$resources.user.setValue.submit({ user_image: url })
      this.currentUser.user_image = url
    },
  },
  pageMeta() {
    return {
      title: [this.profile?.full_name || '', 'Profile'].join(' | '),
    }
  },
}
</script>
