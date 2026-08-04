import { ref } from 'vue'

/**
 * Open state for the customize-sidebar dialog.
 *
 * The dialog is mounted once, in AppRail, but opened from the app menu on the logo.
 * A shared flag keeps those two apart, so the trigger doesn't have to mount its own
 * copy of a fairly heavy drag-and-drop dialog.
 */
export const showCustomizeSidebarDialog = ref(false)

export function openCustomizeSidebarDialog() {
  showCustomizeSidebarDialog.value = true
}
