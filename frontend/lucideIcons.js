import * as LucideIcons from 'lucide-static'

let icons = {}
for (const icon in LucideIcons) {
  icons[icon] = LucideIcons[icon]
  let dashKey = camelToDash(icon)
  if (dashKey !== icon) {
    icons[dashKey] = LucideIcons[icon]
  }
}

export default icons

function camelToDash(key) {
  return key.replace(/([a-z0-9]|(?=[A-Z]))([A-Z])/g, '$1-$2').toLowerCase()
}
