import * as LucideIcons from 'lucide-static'

let icons = {}
for (const icon in LucideIcons) {
  let iconSvg = LucideIcons[icon]
  if (icon == 'default') {
    continue
  }

  // set stroke-width to 1.5
  if (iconSvg && iconSvg.includes('stroke-width')) {
    iconSvg = iconSvg.replace(/stroke-width="2"/g, 'stroke-width="1.5"')
  }

  let dashKey = camelToDash(icon)
  icons[icon] = iconSvg
  if (dashKey !== icon) {
    icons[dashKey] = iconSvg
  }
}

export default icons

function camelToDash(key) {
  return key.replace(/([a-z0-9]|(?=[A-Z]))([A-Z])/g, '$1-$2').toLowerCase()
}
