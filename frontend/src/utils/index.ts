import { dayjs, dayjsLocal, toast, type Dayjs } from 'frappe-ui'

export interface ImgDimensions {
  width: number
  height: number
  ratio: number
}

/**
 * Natural size of an image, or `null` when it cannot be loaded.
 *
 * Resolving on error matters: without it a broken or missing URL leaves the
 * promise pending forever and every caller awaiting it stays suspended.
 */
export function getImgDimensions(imgSrc: string): Promise<ImgDimensions | null> {
  return new Promise((resolve) => {
    let img = new Image()
    img.onload = function () {
      let { width, height } = img
      resolve(height ? { width, height, ratio: width / height } : null)
    }
    img.onerror = function () {
      resolve(null)
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

/**
 * The same moment as `time`, as a plain dayjs object, for measuring time elapsed.
 * Elapsed time does not depend on the timezone, and diffing timezone-aware objects is
 * slow, which adds up in a list that does it for every row.
 */
export function plainInstant(time: Dayjs): Dayjs {
  return dayjs(time.valueOf())
}

/** "3 hours ago" for a server timestamp. Same text as `dayjsLocal(timestamp).fromNow()`. */
export function timeAgo(timestamp: string, withoutSuffix = false): string {
  return plainInstant(dayjsLocal(timestamp)).fromNow(withoutSuffix)
}

/** Takes a server timestamp, or one already converted with `dayjsLocal`. */
export function relativeTimestamp(timestamp: string | Dayjs): string {
  const time = typeof timestamp === 'string' ? dayjsLocal(timestamp) : timestamp
  const instant = plainInstant(time)
  const now = dayjs()
  if (now.diff(instant, 'day') < 3) {
    return instant.fromNow()
  }
  if (now.diff(instant, 'year') < 1) {
    return time.format('D MMM')
  }
  return time.format('D MMM YYYY')
}

/** The full date and time for the Tooltip next to a `relativeTimestamp()`. */
export function fullTimestamp(timestamp: string): string {
  return dayjsLocal(timestamp).format('D MMM YYYY [at] h:mm A')
}

/**
 * Whether an editor body carries nothing a reader would see.
 *
 * TipTap serializes an untouched document as `<p></p>`, so a plain emptiness check on the
 * HTML string is not enough. Media-only bodies (an image, a video, an attachment) have no
 * text but are meaningful, so the check is deliberately structural: strip tags that render
 * nothing on their own and see whether any markup or text survives.
 */
export function isEditorContentEmpty(content: string | null | undefined): boolean {
  const html = (content ?? '').trim()
  if (!html) return true
  if (/<div\b[^>]*\bdata-type="poll"/i.test(html)) return false
  const stripped = html
    .replace(/<(p|div|br|span)\b[^>]*>/gi, '')
    .replace(/<\/(p|div|span)>/gi, '')
    .replace(/&nbsp;/gi, ' ')
    .trim()
  return stripped.length === 0
}

/**
 * One readable sentence about a failed request, to put in front of a person.
 *
 * Frappe's own message is used when it reads as a sentence, without the exception name
 * in front ("PermissionError: You cannot…" becomes "You cannot…"). Everything else becomes
 * `fallback`: "Internal Server Error", tracebacks, empty responses, and JavaScript errors
 * such as "Failed to fetch". Write `fallback` as the failure in plain words
 * ("Could not load discussions.").
 */
export function errorText(error: unknown, fallback: string): string {
  const sentence = serverLines(error).map(withoutExceptionName).find(isReadable)
  return sentence ? asSentence(sentence) : fallback
}

// The lines the server wrote for a person. frappe-ui's v1 requests (`useCall`,
// `createResource`) put them on `messages`; the v2 composables (`useDoc`, `useList`)
// throw an error with the exception name on `type` and "<type>: <text>" on `message`.
function serverLines(error: unknown): string[] {
  if (typeof error === 'string') return error.split('\n')
  if (!(error instanceof Error)) return []
  const { messages, type } = error as Error & { messages?: unknown; type?: unknown }
  if (Array.isArray(messages)) {
    return messages
      .filter((message): message is string => typeof message === 'string')
      .flatMap((message) => stripHtml(message).split('\n'))
  }
  if (typeof type === 'string') return stripHtml(error.message).split('\n')
  return []
}

function withoutExceptionName(line: string): string {
  return line.replace(/^(?:[\w.]+\.)?[A-Z]\w*(?:Error|Exception)\b:?\s*/, '').trim()
}

function isReadable(line: string): boolean {
  if (!line.includes(' ') || line.length > 300) return false
  return !/internal server error|traceback/i.test(line)
}

function asSentence(line: string): string {
  const capitalized = line.charAt(0).toUpperCase() + line.slice(1)
  return /[.!?]$/.test(capitalized) ? capitalized : `${capitalized}.`
}

function stripHtml(value: string) {
  return value.replace(/<[^>]*>/g, '').trim()
}
