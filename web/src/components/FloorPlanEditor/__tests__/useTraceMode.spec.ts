import { describe, expect, it } from 'vitest'

import { useTraceMode } from '@/components/FloorPlanEditor/useTraceMode'

describe('useTraceMode', () => {
  it('starts with empty points', () => {
    const trace = useTraceMode()
    trace.startTrace('living_room')
    expect(trace.tracePoints.value).toEqual([])
    expect(trace.isTraceActive.value).toBe(true)
  })

  it('canClose after three points', () => {
    const trace = useTraceMode()
    trace.startTrace('bedroom')
    trace.addTracePoint({ x: 0, y: 0 }, [])
    trace.addTracePoint({ x: 100, y: 0 }, [])
    expect(trace.canCloseTrace.value).toBe(false)
    trace.addTracePoint({ x: 100, y: 100 }, [])
    expect(trace.canCloseTrace.value).toBe(true)
  })

  it('closeTrace rejects self-intersecting polygon', () => {
    const trace = useTraceMode()
    trace.startTrace('bedroom')
    trace.addTracePoint({ x: 0, y: 0 }, [])
    trace.addTracePoint({ x: 100, y: 100 }, [])
    trace.addTracePoint({ x: 100, y: 0 }, [])
    trace.addTracePoint({ x: 0, y: 100 }, [])
    expect(trace.closeTrace()).toBeNull()
    expect(trace.traceError.value).toContain('自交叉')
  })

  it('undoTracePoint removes last point', () => {
    const trace = useTraceMode()
    trace.startTrace('kitchen')
    trace.addTracePoint({ x: 1, y: 1 }, [])
    trace.addTracePoint({ x: 2, y: 2 }, [])
    trace.undoTracePoint()
    expect(trace.tracePoints.value).toHaveLength(1)
  })

  it('cancelTrace clears state', () => {
    const trace = useTraceMode()
    trace.startTrace('kitchen')
    trace.addTracePoint({ x: 1, y: 1 }, [])
    trace.cancelTrace()
    expect(trace.isTraceActive.value).toBe(false)
    expect(trace.tracePoints.value).toEqual([])
  })
})
