import type { PerspectiveCamera, Vector3 } from 'three'

export interface CollisionBox {
  min: [number, number, number]
  max: [number, number, number]
}

export interface PortalTrigger {
  id: string
  targetRoomId: string
  trigger: CollisionBox
  spawn: [number, number, number]
}

export interface FirstPersonOptions {
  domElement: HTMLElement
  camera: PerspectiveCamera
  collisionBoxes: CollisionBox[]
  portals?: PortalTrigger[]
  onPortalEnter?: (portal: PortalTrigger) => void
  eyeHeight?: number
  moveSpeed?: number
  roomBounds?: { min: { x: number; y: number; z: number }; max: { x: number; y: number; z: number } }
}

const PLAYER_RADIUS = 0.25

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function collides(position: Vector3, boxes: CollisionBox[], radius: number): boolean {
  for (const box of boxes) {
    const nearestX = clamp(position.x, box.min[0], box.max[0])
    const nearestY = clamp(position.y, box.min[1], box.max[1])
    const dx = position.x - nearestX
    const dy = position.y - nearestY
    if (dx * dx + dy * dy < radius * radius) {
      return true
    }
  }
  return false
}

function insideBox(x: number, y: number, box: CollisionBox): boolean {
  return x >= box.min[0] && x <= box.max[0] && y >= box.min[1] && y <= box.max[1]
}

export function useFirstPersonControls(options: FirstPersonOptions) {
  const { domElement, camera, eyeHeight = 1.6, moveSpeed = 3.5, roomBounds, onPortalEnter } = options
  let collisionBoxes = [...options.collisionBoxes]
  let portals = [...(options.portals ?? [])]
  let portalCooldownUntil = 0

  let yaw = 0
  let pitch = 0
  const keys = new Set<string>()
  let locked = false
  let animationId = 0
  let lastTime = performance.now()

  function syncCameraRotation() {
    camera.rotation.order = 'YXZ'
    camera.rotation.y = yaw
    camera.rotation.x = pitch
  }

  function onKeyDown(event: KeyboardEvent) {
    keys.add(event.code)
  }

  function onKeyUp(event: KeyboardEvent) {
    keys.delete(event.code)
  }

  function onMouseMove(event: MouseEvent) {
    if (!locked) return
    yaw -= event.movementX * 0.002
    pitch -= event.movementY * 0.002
    pitch = clamp(pitch, -Math.PI / 2 + 0.05, Math.PI / 2 - 0.05)
    syncCameraRotation()
  }

  function onClick() {
    if (document.pointerLockElement !== domElement) {
      domElement.requestPointerLock()
    }
  }

  function onPointerLockChange() {
    locked = document.pointerLockElement === domElement
  }

  function tryMove(deltaX: number, deltaY: number) {
    const nextX = camera.position.x + deltaX
    const nextY = camera.position.y + deltaY
    const probe = camera.position.clone()
    probe.x = nextX
    if (!collides(probe, collisionBoxes, PLAYER_RADIUS)) {
      camera.position.x = nextX
    }
    probe.x = camera.position.x
    probe.y = nextY
    if (!collides(probe, collisionBoxes, PLAYER_RADIUS)) {
      camera.position.y = nextY
    }
    if (roomBounds) {
      camera.position.x = clamp(camera.position.x, roomBounds.min.x + PLAYER_RADIUS, roomBounds.max.x - PLAYER_RADIUS)
      camera.position.y = clamp(camera.position.y, roomBounds.min.y + PLAYER_RADIUS, roomBounds.max.y - PLAYER_RADIUS)
    }
    camera.position.z = eyeHeight
    checkPortals()
  }

  function checkPortals() {
    if (!onPortalEnter || performance.now() < portalCooldownUntil) return
    for (const portal of portals) {
      if (insideBox(camera.position.x, camera.position.y, portal.trigger)) {
        portalCooldownUntil = performance.now() + 800
        onPortalEnter(portal)
        break
      }
    }
  }

  function tick(now: number) {
    const dt = Math.min((now - lastTime) / 1000, 0.05)
    lastTime = now
    const speed = moveSpeed * dt
    const forwardX = -Math.sin(yaw)
    const forwardY = -Math.cos(yaw)
    const rightX = Math.cos(yaw)
    const rightY = -Math.sin(yaw)

    let moveX = 0
    let moveY = 0
    if (keys.has('KeyW') || keys.has('ArrowUp')) {
      moveX += forwardX * speed
      moveY += forwardY * speed
    }
    if (keys.has('KeyS') || keys.has('ArrowDown')) {
      moveX -= forwardX * speed
      moveY -= forwardY * speed
    }
    if (keys.has('KeyA') || keys.has('ArrowLeft')) {
      moveX -= rightX * speed
      moveY -= rightY * speed
    }
    if (keys.has('KeyD') || keys.has('ArrowRight')) {
      moveX += rightX * speed
      moveY += rightY * speed
    }
    if (moveX !== 0 || moveY !== 0) {
      tryMove(moveX, moveY)
    }
    animationId = requestAnimationFrame(tick)
  }

  function mount() {
    domElement.addEventListener('click', onClick)
    document.addEventListener('pointerlockchange', onPointerLockChange)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    animationId = requestAnimationFrame(tick)
  }

  function dispose() {
    domElement.removeEventListener('click', onClick)
    document.removeEventListener('pointerlockchange', onPointerLockChange)
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('keydown', onKeyDown)
    window.removeEventListener('keyup', onKeyUp)
    cancelAnimationFrame(animationId)
    if (document.pointerLockElement === domElement) {
      document.exitPointerLock()
    }
  }

  function setSpawn(x: number, y: number) {
    camera.position.set(x, y, eyeHeight)
    syncCameraRotation()
  }

  function updateCollisionBoxes(boxes: CollisionBox[]) {
    collisionBoxes = [...boxes]
  }

  function updatePortals(next: PortalTrigger[]) {
    portals = [...next]
  }

  return { mount, dispose, setSpawn, updateCollisionBoxes, updatePortals, syncCameraRotation }
}
