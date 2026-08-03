import { dayjsLocal, toast } from 'frappe-ui'

export function getImgDimensions(
  imgSrc: string,
): Promise<{ width: number; height: number; ratio: number }> {
  return new Promise((resolve) => {
    let img = new Image()
    img.onload = function () {
      let { width, height } = img
      resolve({ width, height, ratio: width / height })
    }
    img.src = imgSrc
  })
}

export async function copyToClipboard(text: string): Promise<void> {
  try {
    // Use modern Clipboard API if available
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      toast.success('Copied to clipboard')
      return
    }

    // Fallback for older browsers or non-secure contexts
    let textField = document.createElement('textarea')
    textField.value = text
    document.body.appendChild(textField)
    textField.focus()
    textField.select()
    document.execCommand('copy')
    textField.remove()
    toast.success('Copied to clipboard')
  } catch (error) {
    toast.error('Failed to copy to clipboard')
    console.error('Failed to copy text to clipboard:', error)
    throw error
  }
}

export function getRandomNumber(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

export function getPlatform(): 'win' | 'mac' | 'linux' | undefined {
  let ua = navigator.userAgent.toLowerCase()
  if (ua.indexOf('win') > -1) {
    return 'win'
  } else if (ua.indexOf('mac') > -1) {
    return 'mac'
  } else if (ua.indexOf('x11') > -1 || ua.indexOf('linux') > -1) {
    return 'linux'
  }
}

export function relativeTimestamp(timestamp: string): string {
  if (dayjsLocal().diff(timestamp, 'day') < 3) {
    return dayjsLocal(timestamp).fromNow()
  }
  if (dayjsLocal().diff(timestamp, 'year') < 1) {
    return dayjsLocal(timestamp).format('D MMM')
  }
  return dayjsLocal(timestamp).format('D MMM YYYY')
}

/**
 * Pull the human-readable text out of a frappe-ui request error.
 *
 * `frappeRequest`/`call` put the clean `frappe.throw()` text on the error's
 * `messages` array (parsed out of `_server_messages`) and leave the noisy
 * "<method> <ExcType>" string on `message`, so prefer `messages`.
 */
export function extractServerMessage(error: unknown): string {
  if (!(error instanceof Error)) return typeof error === 'string' ? error : ''

  let serverMessages = (error as Error & { messages?: unknown }).messages
  if (Array.isArray(serverMessages)) {
    let messages = serverMessages.filter(
      (message): message is string => typeof message === 'string',
    )
    if (messages.length) return stripHtml(messages.join('\n'))
  }
  return error.message ? stripHtml(error.message) : ''
}

function stripHtml(value: string) {
  return value.replace(/<[^>]*>/g, '').trim()
}
