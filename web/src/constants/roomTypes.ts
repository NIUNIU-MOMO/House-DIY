import type { FloorPoint, FloorRoom } from '@/types/floorplan'

export type RoomTypeKey =
  | 'living_room'
  | 'dining_room'
  | 'family_room'
  | 'master_bedroom'
  | 'bedroom'
  | 'secondary_bedroom'
  | 'kids_room'
  | 'elder_room'
  | 'guest_room'
  | 'study'
  | 'kitchen'
  | 'bathroom'
  | 'master_bath'
  | 'secondary_bath'
  | 'laundry'
  | 'entry'
  | 'corridor'
  | 'staircase'
  | 'balcony'
  | 'utility_balcony'
  | 'leisure_balcony'
  | 'terrace'
  | 'garden'
  | 'storage'
  | 'cloakroom'
  | 'multipurpose'
  | 'media_room'
  | 'equipment_platform'

export type RoomNamingStyle = 'letter' | 'number'

export interface RoomTypeOption {
  key: RoomTypeKey
  label: string
  baseName: string
  naming: RoomNamingStyle
}

export interface RoomTypeGroup {
  group: string
  options: RoomTypeOption[]
}

export const ROOM_TYPE_GROUPS: RoomTypeGroup[] = [
  {
    group: '起居',
    options: [
      { key: 'living_room', label: '客厅', baseName: '客厅', naming: 'number' },
      { key: 'dining_room', label: '餐厅', baseName: '餐厅', naming: 'number' },
      { key: 'family_room', label: '起居室', baseName: '起居室', naming: 'number' },
    ],
  },
  {
    group: '卧室',
    options: [
      { key: 'master_bedroom', label: '主卧', baseName: '主卧', naming: 'number' },
      { key: 'bedroom', label: '卧室', baseName: '卧室', naming: 'letter' },
      { key: 'secondary_bedroom', label: '次卧', baseName: '次卧', naming: 'number' },
      { key: 'kids_room', label: '儿童房', baseName: '儿童房', naming: 'number' },
      { key: 'elder_room', label: '长辈房', baseName: '长辈房', naming: 'number' },
      { key: 'guest_room', label: '客房', baseName: '客房', naming: 'number' },
      { key: 'study', label: '书房', baseName: '书房', naming: 'number' },
    ],
  },
  {
    group: '厨卫',
    options: [
      { key: 'kitchen', label: '厨房', baseName: '厨房', naming: 'number' },
      { key: 'bathroom', label: '卫生间', baseName: '卫生间', naming: 'number' },
      { key: 'master_bath', label: '主卫', baseName: '主卫', naming: 'number' },
      { key: 'secondary_bath', label: '次卫', baseName: '次卫', naming: 'number' },
      { key: 'laundry', label: '洗衣间', baseName: '洗衣间', naming: 'number' },
    ],
  },
  {
    group: '交通',
    options: [
      { key: 'entry', label: '玄关', baseName: '玄关', naming: 'number' },
      { key: 'corridor', label: '走廊', baseName: '走廊', naming: 'number' },
      { key: 'staircase', label: '楼梯', baseName: '楼梯', naming: 'number' },
    ],
  },
  {
    group: '附属',
    options: [
      { key: 'balcony', label: '阳台', baseName: '阳台', naming: 'letter' },
      { key: 'utility_balcony', label: '生活阳台', baseName: '生活阳台', naming: 'number' },
      { key: 'leisure_balcony', label: '休闲阳台', baseName: '休闲阳台', naming: 'number' },
      { key: 'terrace', label: '露台', baseName: '露台', naming: 'number' },
      { key: 'garden', label: '花园', baseName: '花园', naming: 'number' },
    ],
  },
  {
    group: '功能',
    options: [
      { key: 'storage', label: '储物间', baseName: '储物间', naming: 'number' },
      { key: 'cloakroom', label: '衣帽间', baseName: '衣帽间', naming: 'number' },
      { key: 'multipurpose', label: '多功能室', baseName: '多功能室', naming: 'number' },
      { key: 'media_room', label: '影音室', baseName: '影音室', naming: 'number' },
      { key: 'equipment_platform', label: '设备平台', baseName: '设备平台', naming: 'number' },
    ],
  },
]

export const ROOM_TYPE_OPTIONS: RoomTypeOption[] = ROOM_TYPE_GROUPS.flatMap((group) => group.options)

export const DEFAULT_ROOM_TYPE: RoomTypeKey = 'bedroom'

const LETTER_SUFFIX_TYPES = new Set<RoomTypeKey>(['bedroom', 'balcony'])

function getRoomTypeOption(key: RoomTypeKey): RoomTypeOption {
  const option = ROOM_TYPE_OPTIONS.find((item) => item.key === key)
  if (!option) {
    throw new Error(`Unknown room type: ${key}`)
  }
  return option
}

function nextLetterSuffix(existingNames: string[], baseName: string): string {
  const used = new Set<string>()
  const pattern = new RegExp(`^${baseName}([A-Z])?$`)
  for (const name of existingNames) {
    const match = pattern.exec(name)
    if (!match) {
      continue
    }
    used.add(match[1] ?? 'A')
  }
  if (!used.has('A')) {
    return `${baseName}A`
  }
  for (let code = 66; code <= 90; code += 1) {
    const letter = String.fromCharCode(code)
    if (!used.has(letter)) {
      return `${baseName}${letter}`
    }
  }
  return `${baseName}Z`
}

function nextNumberSuffix(existingNames: string[], baseName: string): string {
  if (!existingNames.includes(baseName)) {
    return baseName
  }
  let index = 2
  while (existingNames.includes(`${baseName}${index}`)) {
    index += 1
  }
  return `${baseName}${index}`
}

export function buildRoomName(typeKey: RoomTypeKey, existingRooms: Pick<FloorRoom, 'name'>[]): string {
  const option = getRoomTypeOption(typeKey)
  const names = existingRooms.map((room) => room.name)
  if (option.naming === 'letter' || LETTER_SUFFIX_TYPES.has(typeKey)) {
    return nextLetterSuffix(names, option.baseName)
  }
  return nextNumberSuffix(names, option.baseName)
}

export function nextRoomId(rooms: Pick<FloorRoom, 'id'>[]): string {
  let max = 0
  for (const room of rooms) {
    const match = /^r(\d+)$/.exec(room.id)
    if (match) {
      max = Math.max(max, Number(match[1]))
    }
  }
  return `r${max + 1}`
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

export function defaultPolygonAt(
  center: FloorPoint,
  sourceWidth: number,
  sourceHeight: number,
): FloorPoint[] {
  const shortEdge = Math.min(sourceWidth, sourceHeight)
  const half = Math.min(60, shortEdge * 0.04)
  const left = clamp(center.x - half, 0, sourceWidth)
  const right = clamp(center.x + half, 0, sourceWidth)
  const top = clamp(center.y - half, 0, sourceHeight)
  const bottom = clamp(center.y + half, 0, sourceHeight)
  return [
    { x: left, y: top },
    { x: right, y: top },
    { x: right, y: bottom },
    { x: left, y: bottom },
  ]
}

export function polygonArea(polygon: FloorPoint[]): number {
  if (polygon.length < 3) {
    return 0
  }
  let sum = 0
  for (let index = 0; index < polygon.length; index += 1) {
    const current = polygon[index]!
    const next = polygon[(index + 1) % polygon.length]!
    sum += current.x * next.y - next.x * current.y
  }
  return Math.abs(sum) / 2
}

export function computeRoomArea(polygon: FloorPoint[], scale: number | null): number | null {
  if (null == scale || scale <= 0) {
    return null
  }
  const sqm = polygonArea(polygon) / (scale * scale)
  return Math.round(sqm * 100) / 100
}
