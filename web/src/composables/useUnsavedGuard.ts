import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

const UNSAVED_GUARD_KEY: InjectionKey<() => Promise<boolean>> = Symbol('unsavedGuard')

/**
 * 注册未保存变更拦截（双层确认）
 */
export function useUnsavedGuard(isDirty: Ref<boolean>) {
  const showing = ref(false)

  async function confirmLeave(): Promise<boolean> {
    if (!isDirty.value || showing.value) {
      return true
    }

    const leave = window.confirm('有未保存的变更\n\n请先保存，或选择放弃并离开。')
    if (!leave) {
      return false
    }

    showing.value = true
    const discard = window.confirm('未保存的修改将丢失，确定放弃？')
    showing.value = false
    if (discard) {
      isDirty.value = false
    }
    return discard
  }

  provide(UNSAVED_GUARD_KEY, confirmLeave)

  onBeforeRouteLeave(async (_to, _from, next) => {
    if (await confirmLeave()) {
      next()
      return
    }
    next(false)
  })

  return { confirmLeave }
}

/**
 * 流程条切换前调用
 */
export function useUnsavedGuardConsumer() {
  return inject(UNSAVED_GUARD_KEY, async () => true)
}
