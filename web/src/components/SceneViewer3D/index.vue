<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

import {
  useFirstPersonControls,
  type CollisionBox,
  type PortalTrigger,
} from './useFirstPersonControls'

export interface ScenePortal {
  id: string
  source_room_id: string
  target_room_id: string
  target_room_name: string
  trigger: CollisionBox
  spawn: [number, number, number]
}

export interface SceneRoomMeta {
  id: string
  name: string
  bounds: {
    min: { x: number; y: number; z: number }
    max: { x: number; y: number; z: number }
  }
  collision_boxes: CollisionBox[]
  portals?: ScenePortal[]
}

const props = defineProps<{
  gltfUrl: string
  /** scene.json 中的文件名，用于区分 GLB 与旧版 glTF+bin */
  modelFile?: string
  rooms: SceneRoomMeta[]
  activeRoomId: string
}>()

const emit = defineEmits<{
  roomChange: [roomId: string]
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const portalHint = ref<string | null>(null)

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: ReturnType<typeof useFirstPersonControls> | null = null
let resizeObserver: ResizeObserver | null = null

const activeRoom = computed(() =>
  props.rooms.find((room) => room.id === props.activeRoomId) ?? props.rooms[0],
)

const activePortals = computed(() => activeRoom.value?.portals ?? [])

function toPortalTriggers(portals: ScenePortal[]): PortalTrigger[] {
  return portals.map((portal) => ({
    id: portal.id,
    targetRoomId: portal.target_room_id,
    trigger: portal.trigger,
    spawn: portal.spawn,
  }))
}

function applyRoom(room: SceneRoomMeta | undefined) {
  if (!room || !controls || !camera) return
  controls.updateCollisionBoxes(room.collision_boxes)
  controls.updatePortals(toPortalTriggers(room.portals ?? []))
  portalHint.value =
    room.portals && room.portals.length > 0
      ? `门洞 → ${room.portals.map((p) => p.target_room_name).join(' / ')}`
      : null
}

function handlePortalEnter(portal: PortalTrigger) {
  emit('roomChange', portal.targetRoomId)
  controls?.setSpawn(portal.spawn[0], portal.spawn[1])
  applyRoom(props.rooms.find((room) => room.id === portal.targetRoomId))
}

async function loadScene() {
  if (!containerRef.value) return
  loading.value = true
  error.value = null

  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x2a2824)

  camera = new THREE.PerspectiveCamera(70, width / height, 0.05, 100)
  camera.up.set(0, 0, 1)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setSize(width, height)
  containerRef.value.innerHTML = ''
  containerRef.value.appendChild(renderer.domElement)

  scene.add(new THREE.AmbientLight(0xffffff, 0.75))
  const sun = new THREE.DirectionalLight(0xfff2e0, 1.0)
  sun.position.set(4, 6, 8)
  scene.add(sun)
  const fill = new THREE.DirectionalLight(0xc8d8ff, 0.35)
  fill.position.set(-3, -2, 5)
  scene.add(fill)

  const loader = new GLTFLoader()
  const needsExternalAssets = (props.modelFile ?? '').endsWith('.gltf')
  if (needsExternalAssets) {
    const assetsBase = props.gltfUrl.replace(/\/gltf$/, '/assets/')
    loader.setPath(assetsBase)
  }
  try {
    const gltf = await loader.loadAsync(props.gltfUrl)
    gltf.scene.traverse((child) => {
      if (!(child instanceof THREE.Mesh)) {
        return
      }
      child.castShadow = true
      child.receiveShadow = true
      const material = child.material
      const materials = Array.isArray(material) ? material : [material]
      for (const entry of materials) {
        if (!entry) {
          continue
        }
        if (child.geometry.attributes.color) {
          entry.vertexColors = true
        }
        if (entry instanceof THREE.MeshStandardMaterial) {
          entry.roughness = 0.85
          entry.metalness = 0.05
        }
      }
    })
    scene.add(gltf.scene)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'glTF 加载失败'
    loading.value = false
    return
  }

  const active = activeRoom.value
  controls = useFirstPersonControls({
    domElement: renderer.domElement,
    camera,
    collisionBoxes: active?.collision_boxes ?? [],
    portals: toPortalTriggers(active?.portals ?? []),
    roomBounds: active?.bounds,
    onPortalEnter: handlePortalEnter,
  })
  controls.mount()
  if (active) {
    const center = {
      x: (active.bounds.min.x + active.bounds.max.x) / 2,
      y: (active.bounds.min.y + active.bounds.max.y) / 2,
    }
    controls.setSpawn(center.x, center.y)
    applyRoom(active)
  }

  const renderLoop = () => {
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
    requestAnimationFrame(renderLoop)
  }
  renderLoop()

  resizeObserver = new ResizeObserver(() => {
    if (!containerRef.value || !renderer || !camera) return
    const nextWidth = containerRef.value.clientWidth
    const nextHeight = containerRef.value.clientHeight
    camera.aspect = nextWidth / nextHeight
    camera.updateProjectionMatrix()
    renderer.setSize(nextWidth, nextHeight)
  })
  resizeObserver.observe(containerRef.value)
  loading.value = false
}

function selectRoom(roomId: string) {
  emit('roomChange', roomId)
  const room = props.rooms.find((item) => item.id === roomId)
  if (room && controls) {
    const center = {
      x: (room.bounds.min.x + room.bounds.max.x) / 2,
      y: (room.bounds.min.y + room.bounds.max.y) / 2,
    }
    controls.setSpawn(center.x, center.y)
    applyRoom(room)
  }
}

watch(
  () => props.activeRoomId,
  () => applyRoom(activeRoom.value),
)

onMounted(loadScene)

onBeforeUnmount(() => {
  controls?.dispose()
  resizeObserver?.disconnect()
  renderer?.dispose()
})
</script>

<template>
  <div class="viewer-full">
    <div ref="containerRef" class="viewer-3d" />
    <div v-if="loading" class="viewer-overlay">加载 3D 场景…</div>
    <div v-if="error" class="viewer-overlay error">{{ error }}</div>
    <div class="viewer-hud">
      <span>{{ activeRoom?.name ?? '—' }}</span>
      <span class="muted">WASD 移动 · 点击锁定鼠标 · 走近门洞切换房间</span>
      <span v-if="portalHint" class="portal-hint">{{ portalHint }}</span>
    </div>
    <aside class="viewer-sidebar">
      <h4>房间切换</h4>
      <ul class="room-jump">
        <li
          v-for="room in rooms"
          :key="room.id"
          :class="{ active: room.id === activeRoomId }"
          @click="selectRoom(room.id)"
        >
          {{ room.name }}
        </li>
      </ul>
    </aside>
  </div>
</template>

<style scoped>
.viewer-full {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 200px;
  min-height: calc(100vh - 80px);
  background: #111;
}

.viewer-3d {
  min-height: calc(100vh - 80px);
  cursor: crosshair;
}

.viewer-3d :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}

.viewer-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #ddd;
  pointer-events: none;
}

.viewer-overlay.error {
  color: #d48f8f;
}

.viewer-hud {
  position: absolute;
  top: 1rem;
  left: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background: rgba(0, 0, 0, 0.55);
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
}

.portal-hint {
  color: #8fd4a8;
  font-size: 0.75rem;
}

.viewer-sidebar {
  background: var(--bg-panel);
  border-left: 1px solid #333;
  padding: 1rem;
}

.viewer-sidebar h4 {
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
}

.room-jump {
  list-style: none;
}

.room-jump li {
  padding: 0.45rem 0.55rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  color: #bbb;
}

.room-jump li.active,
.room-jump li:hover {
  background: #2c4a3e;
  color: #8fd4a8;
}

.muted {
  color: #888;
  font-size: 0.75rem;
}
</style>
