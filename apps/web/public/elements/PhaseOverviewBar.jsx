import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { CalendarRange, Flag, Layers, Target } from "lucide-react"

function clampPercent(value) {
    if (!Number.isFinite(value)) return 0
    return Math.max(0, Math.min(100, value))
}

function jumpToWeek(weekIndex) {
    const targetId = `week-${weekIndex}`
    const target = typeof document !== "undefined" ? document.getElementById(targetId) : null

    if (target?.scrollIntoView) {
        target.scrollIntoView({ behavior: "smooth", block: "start" })
        return
    }

    if (typeof window !== "undefined" && window.location) {
        window.location.hash = targetId
    }
}

export default function PhaseOverviewBar() {
    const p = typeof props === "undefined" ? {} : props
    const planMeta = p.plan_meta || {}
    const phases = Array.isArray(p.phase_summary) ? p.phase_summary : []
    const totalWeeks = Number(planMeta.actual_weeks || planMeta.requested_weeks || 0)
    const currentWeek = Number(p.current_week || 1)
    const currentPhase = p.current_phase || ""
    const goal = planMeta.goal || "训练计划"

    const safeTotalWeeks = totalWeeks > 0 ? totalWeeks : phases.reduce((max, phase) => {
        return Math.max(max, Number(phase.end_week || 0))
    }, 0)

    if (!phases.length || !safeTotalWeeks) {
        return null
    }

    const progressPercent = clampPercent((currentWeek / safeTotalWeeks) * 100)
    const phaseNow = phases.find((phase) => {
        const startWeek = Number(phase.start_week || 1)
        const endWeek = Number(phase.end_week || startWeek)
        return currentWeek >= startWeek && currentWeek <= endWeek
    })

    return (
        <Card className="mb-4 rounded-lg border-border/70 p-4 shadow-sm sm:p-5">
            <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 space-y-2">
                        <div className="flex items-center gap-2">
                            <Layers className="h-5 w-5 shrink-0 text-primary" />
                            <span className="text-sm font-semibold">阶段总览</span>
                        </div>
                        <div className="flex min-w-0 items-start gap-2">
                            <Target className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                            <p className="min-w-0 text-sm leading-6 text-foreground">{goal}</p>
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-2 sm:justify-end">
                        <Badge variant="secondary" className="gap-1 text-xs">
                            <CalendarRange className="h-3.5 w-3.5" />
                            {safeTotalWeeks} 周
                        </Badge>
                        <Badge variant="outline" className="gap-1 text-xs">
                            <Flag className="h-3.5 w-3.5" />
                            第 {currentWeek} 周
                        </Badge>
                    </div>
                </div>

                <div className="space-y-2">
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                        <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>

                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                        {phases.map((phase, idx) => {
                            const startWeek = Number(phase.start_week || 1)
                            const endWeek = Number(phase.end_week || startWeek)
                            const weekCount = Number(phase.week_count || Math.max(1, endWeek - startWeek + 1))
                            const name = phase.phase || `阶段 ${idx + 1}`
                            const objective = phase.objective || ""
                            const isCurrent = currentWeek >= startWeek && currentWeek <= endWeek
                            const width = clampPercent((weekCount / safeTotalWeeks) * 100)

                            return (
                                <Button
                                    key={`${name}-${startWeek}-${endWeek}`}
                                    type="button"
                                    variant="ghost"
                                    className={`h-auto justify-start rounded-md border p-3 text-left hover:bg-muted/70 ${
                                        isCurrent ? "border-primary/50 bg-primary/5" : "border-border/70"
                                    }`}
                                    onClick={() => jumpToWeek(startWeek)}
                                    title={`跳转到第 ${startWeek} 周`}
                                >
                                    <div className="min-w-0 flex-1 space-y-2">
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="truncate text-sm font-medium">{name}</span>
                                            <span className="shrink-0 text-xs text-muted-foreground">
                                                W{startWeek}-W{endWeek}
                                            </span>
                                        </div>
                                        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                                            <div
                                                className={isCurrent ? "h-full rounded-full bg-primary" : "h-full rounded-full bg-muted-foreground/40"}
                                                style={{ width: `${width}%` }}
                                            />
                                        </div>
                                        {objective && (
                                            <p className="max-h-10 overflow-hidden text-xs leading-5 text-muted-foreground">
                                                {objective}
                                            </p>
                                        )}
                                    </div>
                                </Button>
                            )
                        })}
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>当前阶段</span>
                    <Badge variant="outline" className="text-xs">
                        {currentPhase || phaseNow?.phase || "训练期"}
                    </Badge>
                </div>
            </div>
        </Card>
    )
}
