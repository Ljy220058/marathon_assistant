import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import {
    Calendar, ChevronLeft, ChevronRight, Flame, Zap, Timer,
    Heart, Lightbulb, AlertTriangle, Shield, Bookmark,
    StickyNote, FileText, Info, LayoutGrid
} from "lucide-react"
import { useState, useMemo } from "react"

const MONTH_NAMES = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

const DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

const TRAINING_BADGES = {
    "轻松跑": "bg-green-500/10 text-green-500 border-green-500/20",
    "渐进跑": "bg-green-500/10 text-green-500 border-green-500/20",
    "长距离": "bg-blue-500/10 text-blue-500 border-blue-500/20",
    "节奏跑": "bg-orange-500/10 text-orange-500 border-orange-500/20",
    "间歇跑": "bg-red-500/10 text-red-500 border-red-500/20",
    "休息": "bg-gray-400/10 text-gray-400 border-gray-400/20",
    "恢复跑": "bg-teal-500/10 text-teal-500 border-teal-500/20",
    "法特莱克": "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    "坡道跑": "bg-purple-500/10 text-purple-500 border-purple-500/20",
    "短冲": "bg-pink-500/10 text-pink-500 border-pink-500/20",
    "比赛模拟": "bg-red-500/10 text-red-500 border-red-500/20",
    "配速训练": "bg-cyan-500/10 text-cyan-500 border-cyan-500/20",
}

const EVIDENCE_TIER_BADGES = {
    action_library: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30",
    kb_fallback: "bg-amber-500/10 text-amber-500 border-amber-500/30",
    plan_only: "bg-gray-400/10 text-gray-400 border-gray-400/30",
    needs_evidence: "bg-rose-500/10 text-rose-500 border-rose-500/30",
}

const DEFAULT_EVIDENCE_TIER_LABELS = {
    action_library: "动作库课表",
    kb_fallback: "参考知识库生成",
    plan_only: "基础计划",
    needs_evidence: "待补证据",
}

const ZONE_COLORS = {
    Z1: "bg-blue-200/10 text-blue-600",
    Z2: "bg-green-200/10 text-green-600",
    Z3: "bg-green-400/10 text-green-700",
    Z4: "bg-yellow-300/10 text-yellow-700",
    Z5: "bg-orange-300/10 text-orange-700",
    Z6: "bg-orange-500/10 text-orange-600",
    Z7: "bg-red-400/10 text-red-600",
    Z8: "bg-red-500/10 text-red-700",
    Z9: "bg-purple-500/10 text-purple-700",
}

function getZoneColor(zoneRange) {
    if (!zoneRange) return "bg-muted/10 text-muted-foreground"
    const zones = String(zoneRange).replace(/→/g, "-").split("-")
    for (const zone of zones) {
        const zoneName = zone.trim()
        if (ZONE_COLORS[zoneName]) return ZONE_COLORS[zoneName]
    }
    return "bg-muted/10 text-muted-foreground"
}

function getTrainingBadge(trainingType) {
    return TRAINING_BADGES[trainingType] || "bg-primary/10 text-primary border-primary/20"
}

function getEvidenceTierLabel(day, evidenceTierMap) {
    const tier = day?.evidence_tier || "plan_only"
    return day?.evidence_tier_label || evidenceTierMap[tier] || DEFAULT_EVIDENCE_TIER_LABELS[tier] || "基础计划"
}

function getMonthKey(year, month) {
    return `${year}-${String(month).padStart(2, "0")}`
}

function getDayNumber(day) {
    if (day?.date_str) {
        const parsed = Number(String(day.date_str).slice(8, 10))
        if (Number.isFinite(parsed) && parsed > 0) return parsed
    }
    return day?.day_index || 0
}

function getMondayFirstOffset(dateString) {
    if (!dateString) return 0
    const date = new Date(`${dateString}T00:00:00`)
    if (Number.isNaN(date.getTime())) return 0
    return (date.getDay() + 6) % 7
}

function CalendarDayCell({ day, onClick }) {
    if (!day) return <div className="min-h-24 rounded-md border border-transparent" />

    const isRest = Boolean(day.is_rest)
    const trainingBadge = isRest ? getTrainingBadge("休息") : getTrainingBadge(day.training_type)
    const zoneLabel = day.zone_range || day.zone_label || ""
    const dayNumber = getDayNumber(day)
    const trainingLabel = day.training_type_label || day.training_type || (isRest ? "休息" : "未安排")

    return (
        <button
            type="button"
            className={`min-h-24 w-full rounded-md border p-2 text-left transition-colors hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 ${isRest ? "opacity-70" : ""}`}
            onClick={() => onClick(day)}
        >
            <div className="flex h-full min-w-0 flex-col gap-1">
                <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-muted-foreground">
                        {dayNumber ? `${dayNumber}日` : day.day_label}
                    </span>
                    <span
                        className={`h-1.5 w-1.5 shrink-0 rounded-full ${day.evidence_tier === "action_library" ? "bg-emerald-400" : day.evidence_tier === "kb_fallback" ? "bg-amber-400" : day.evidence_tier === "needs_evidence" ? "bg-rose-400" : "bg-gray-300"}`}
                    />
                </div>
                <div className="flex min-h-0 flex-1 flex-col justify-center">
                    <Badge variant="outline" className={`max-w-full truncate px-1 py-0 text-[10px] leading-tight ${trainingBadge}`}>
                        {trainingLabel}
                    </Badge>
                </div>
                {!isRest && zoneLabel && (
                    <div className="flex min-w-0 items-center gap-1">
                        <Heart className="h-2.5 w-2.5 shrink-0 text-red-400" />
                        <span className="truncate text-[10px] text-muted-foreground">{zoneLabel}</span>
                    </div>
                )}
                {isRest && (
                    <span className="text-[10px] text-muted-foreground">恢复日</span>
                )}
            </div>
        </button>
    )
}

function DayDetailSheet({ day, open, onOpenChange, evidenceTierMap }) {
    if (!day) return null

    const isRest = Boolean(day.is_rest)
    const evidenceLabel = getEvidenceTierLabel(day, evidenceTierMap)

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent side="right" className="w-[90vw] max-w-[540px] overflow-y-auto sm:w-[540px]">
                <SheetHeader>
                    <SheetTitle>{day.date_str || `${day.day_label} 课表详情`}</SheetTitle>
                    <SheetDescription>
                        第 {day.week_index} 周 · {day.day_label}
                    </SheetDescription>
                </SheetHeader>

                <div className="mt-6 space-y-4">
                    <div className="flex flex-wrap gap-2">
                        <Badge variant="outline" className={`text-xs ${getTrainingBadge(isRest ? "休息" : day.training_type)}`}>
                            {day.training_type_label || day.training_type || (isRest ? "休息" : "未安排")}
                        </Badge>
                        {!isRest && (day.intensity_target || day.zone_range) && (
                            <Badge variant="outline" className={`text-xs ${getZoneColor(day.zone_range)}`}>
                                强度：{day.intensity_target || day.zone_range}
                            </Badge>
                        )}
                        <Badge variant="outline" className={`text-xs ${EVIDENCE_TIER_BADGES[day.evidence_tier] || ""}`}>
                            {evidenceLabel}
                        </Badge>
                    </div>

                    {isRest && (
                        <Card className="bg-muted/20 p-3">
                            <div className="flex items-start gap-2">
                                <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                                <p className="text-sm text-muted-foreground">
                                    {day.training_objective || "休息日，建议充分恢复。可进行轻度交叉训练或拉伸。"}
                                </p>
                            </div>
                        </Card>
                    )}

                    {!isRest && (
                        <>
                            {day.training_objective && (
                                <Card className="bg-muted/20 p-3">
                                    <div className="mb-1 flex items-center gap-2">
                                        <Lightbulb className="h-4 w-4 text-amber-500" />
                                        <span className="text-sm font-medium">训练目标</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground">{day.training_objective}</p>
                                </Card>
                            )}

                            {day.warmup && (
                                <div className="flex items-start gap-2">
                                    <Zap className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
                                    <div className="text-sm">
                                        <span className="font-medium">热身：</span>
                                        {day.warmup}
                                    </div>
                                </div>
                            )}

                            {day.main_set && (
                                <div className="flex items-start gap-2">
                                    <Flame className="mt-0.5 h-4 w-4 shrink-0 text-orange-500" />
                                    <div className="text-sm">
                                        <span className="font-medium">主课：</span>
                                        {day.main_set}
                                    </div>
                                </div>
                            )}

                            {day.cooldown && (
                                <div className="flex items-start gap-2">
                                    <Timer className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
                                    <div className="text-sm">
                                        <span className="font-medium">放松：</span>
                                        {day.cooldown}
                                    </div>
                                </div>
                            )}

                            {day.alternative && (
                                <div className="flex items-start gap-2">
                                    <Shield className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />
                                    <div className="text-sm">
                                        <span className="font-medium">替代训练：</span>
                                        {day.alternative}
                                    </div>
                                </div>
                            )}

                            {!day.intensity_target && (day.zone_label || day.zone_range) && (
                                <div className="flex items-start gap-2">
                                    <Heart className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                                    <div className="text-sm">
                                        <span className="font-medium">建议区间：</span>
                                        {day.zone_label || day.zone_range}
                                    </div>
                                </div>
                            )}
                        </>
                    )}

                    <Separator />

                    <div>
                        <div className="mb-2 flex items-center gap-2">
                            <Bookmark className="h-4 w-4 text-primary" />
                            <span className="text-sm font-medium">证据状态</span>
                        </div>
                        <Card className="bg-muted/20 p-3">
                            <div className="mb-1 flex items-center gap-2">
                                <Badge variant="outline" className={`text-xs ${EVIDENCE_TIER_BADGES[day.evidence_tier] || ""}`}>
                                    {evidenceLabel}
                                </Badge>
                            </div>
                            {day.evidence_tier === "action_library" && (
                                <p className="text-xs text-muted-foreground">
                                    课表数据来自动作库直接证据，训练方案已通过动作库规则匹配。
                                </p>
                            )}
                            {day.evidence_tier === "kb_fallback" && (
                                <p className="text-xs text-muted-foreground">
                                    动作库中未找到该训练类型的直接证据，已基于知识库内容生成参考课表。建议结合个人体感调整。
                                </p>
                            )}
                            {day.evidence_tier === "plan_only" && (
                                <p className="text-xs text-muted-foreground">
                                    当前训练安排来自训练计划骨架，后续可补充动作库或训练数据以获得更精确的课表。
                                </p>
                            )}
                            {day.evidence_tier === "needs_evidence" && (
                                <p className="text-xs text-muted-foreground">
                                    当前训练类型仍需补充证据，请谨慎执行并优先参考教练或可靠训练资料。
                                </p>
                            )}
                            {Array.isArray(day.source) && day.source.length > 0 && (
                                <div className="mt-2">
                                    <p className="mb-1 text-xs font-medium text-muted-foreground">信息来源：</p>
                                    {day.source.map((src, idx) => (
                                        <p key={idx} className="text-xs text-muted-foreground">· {src}</p>
                                    ))}
                                </div>
                            )}
                        </Card>
                    </div>

                    {day.explanation && (
                        <ExplanationSection explanation={day.explanation} />
                    )}

                    {!day.explanation && !isRest && day.training_type !== "休息" && (
                        <Card className="bg-muted/10 p-3">
                            <div className="flex items-start gap-2">
                                <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                                <p className="text-xs text-muted-foreground">
                                    该训练日暂无详细训练解释。
                                </p>
                            </div>
                        </Card>
                    )}

                    {day.notes && (
                        <div className="flex items-start gap-2">
                            <StickyNote className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                            <p className="text-xs text-muted-foreground">{day.notes}</p>
                        </div>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    )
}

function ExplanationSection({ explanation }) {
    const [expanded, setExpanded] = useState(false)

    if (!explanation) return null

    const hasValue = (value) => value && value !== "—" && value !== "-"

    return (
        <div>
            <Separator />
            <div className="mt-2">
                <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start gap-2 text-sm font-medium"
                    onClick={() => setExpanded(!expanded)}
                >
                    <Bookmark className="h-4 w-4" />
                    查看训练解释
                    <span className="ml-auto text-xs text-muted-foreground">
                        {expanded ? "收起 ▲" : "展开 ▼"}
                    </span>
                </Button>

                {expanded && (
                    <Card className="mt-2 space-y-3 bg-muted/10 p-4">
                        {hasValue(explanation.why_scheduled) && (
                            <div>
                                <div className="mb-1 flex items-center gap-1.5">
                                    <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
                                    <span className="text-xs font-semibold">为什么这样安排</span>
                                </div>
                                <p className="text-xs leading-relaxed text-muted-foreground">
                                    {explanation.why_scheduled}
                                    {Array.isArray(explanation.evidence_ids) && explanation.evidence_ids.length > 0 && (
                                        <span className="ml-1 text-blue-500">
                                            {explanation.evidence_ids.map(id => `[${id}]`).join(" ")}
                                        </span>
                                    )}
                                </p>
                            </div>
                        )}

                        {hasValue(explanation.primary_target) && (
                            <div>
                                <div className="mb-1 flex items-center gap-1.5">
                                    <Flame className="h-3.5 w-3.5 text-orange-500" />
                                    <span className="text-xs font-semibold">主要训练目标</span>
                                </div>
                                <p className="text-xs leading-relaxed text-muted-foreground">
                                    {explanation.primary_target}
                                </p>
                            </div>
                        )}

                        {hasValue(explanation.risk_alert) && (
                            <div>
                                <div className="mb-1 flex items-center gap-1.5">
                                    <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                                    <span className="text-xs font-semibold">风险提醒</span>
                                </div>
                                <p className="text-xs leading-relaxed text-muted-foreground">
                                    {explanation.risk_alert}
                                </p>
                            </div>
                        )}

                        {hasValue(explanation.alternative_workout) && (
                            <div>
                                <div className="mb-1 flex items-center gap-1.5">
                                    <Shield className="h-3.5 w-3.5 text-indigo-500" />
                                    <span className="text-xs font-semibold">状态不佳时替代</span>
                                </div>
                                <p className="text-xs leading-relaxed text-muted-foreground">
                                    {explanation.alternative_workout}
                                </p>
                            </div>
                        )}

                        {Array.isArray(explanation.target_labels) && explanation.target_labels.length > 0 && (
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="text-xs text-muted-foreground">目标标签：</span>
                                {explanation.target_labels.map((label, idx) => (
                                    <Badge key={idx} variant="secondary" className="text-[10px]">
                                        {label}
                                    </Badge>
                                ))}
                            </div>
                        )}

                        {hasValue(explanation.decision_summary) && (
                            <div>
                                <div className="mb-1 flex items-center gap-1.5">
                                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                                    <span className="text-xs font-semibold">决策摘要</span>
                                </div>
                                <p className="text-xs leading-relaxed text-muted-foreground">
                                    {explanation.decision_summary}
                                </p>
                            </div>
                        )}

                        {hasValue(explanation.explanation_source) && (
                            <div className="flex items-center gap-1.5">
                                <Info className="h-3 w-3 text-muted-foreground" />
                                <span className="text-[10px] text-muted-foreground">
                                    解释来源：{explanation.explanation_source}
                                </span>
                            </div>
                        )}
                    </Card>
                )}
            </div>
        </div>
    )
}

function YearlyOverview({ monthSummaries, onSelectMonth }) {
    if (!monthSummaries || monthSummaries.length === 0) {
        return (
            <Card className="p-4">
                <p className="text-center text-xs text-muted-foreground">暂无年度训练数据</p>
            </Card>
        )
    }

    return (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
            {monthSummaries.map((summary, idx) => {
                const hasDays = Number(summary.total_days || 0) > 0
                return (
                    <Card
                        key={`${summary.year || "year"}-${summary.month || idx}`}
                        className={`cursor-pointer p-3 transition-colors hover:bg-muted/30 ${!hasDays ? "opacity-40" : ""}`}
                        onClick={() => hasDays && onSelectMonth(summary.year, summary.month)}
                    >
                        <div className="mb-1 flex items-center justify-between gap-2">
                            <span className="truncate text-sm font-medium">
                                {summary.year}年{MONTH_NAMES[(summary.month || 1) - 1]}
                            </span>
                            <Badge variant="secondary" className="shrink-0 text-[10px]">
                                {summary.total_days || 0}天
                            </Badge>
                        </div>
                        {hasDays && (
                            <div className="mt-1 flex gap-0.5">
                                {summary.action_library > 0 && (
                                    <div className="h-1 flex-1 rounded bg-emerald-400" title={`动作库：${summary.action_library}天`} />
                                )}
                                {summary.kb_fallback > 0 && (
                                    <div className="h-1 flex-1 rounded bg-amber-400" title={`参考生成：${summary.kb_fallback}天`} />
                                )}
                                {summary.plan_only > 0 && (
                                    <div className="h-1 flex-1 rounded bg-gray-300" title={`基础计划：${summary.plan_only}天`} />
                                )}
                            </div>
                        )}
                        {!hasDays && (
                            <p className="text-[10px] text-muted-foreground">无训练安排</p>
                        )}
                    </Card>
                )
            })}
        </div>
    )
}

export default function MonthlyTrainingCalendar() {
    const p = typeof props !== "undefined" ? props : {}
    const allDays = Array.isArray(p.days) ? p.days : []
    const phases = Array.isArray(p.phases) ? p.phases : []
    const evidenceSummary = p.evidence_summary || {}
    const evidenceTierMap = p.evidence_tier_map || {}
    const availableMonths = Array.isArray(p.available_months) ? p.available_months : []
    const monthSummaries = Array.isArray(p.month_summaries) ? p.month_summaries : []

    const [viewYear, setViewYear] = useState(p.year ?? 2026)
    const [viewMonth, setViewMonth] = useState(p.month ?? 5)
    const [showYearlyOverview, setShowYearlyOverview] = useState(false)
    const [selectedDay, setSelectedDay] = useState(null)
    const [sheetOpen, setSheetOpen] = useState(false)

    const availableMonthKeys = useMemo(
        () => new Set(
            availableMonths
                .filter(item => item && item.year && item.month)
                .map(item => getMonthKey(item.year, item.month))
        ),
        [availableMonths]
    )

    const handleDayClick = (day) => {
        setSelectedDay(day)
        setSheetOpen(true)
    }

    const handleMonthSelect = (year, month) => {
        setViewYear(Number(year))
        setViewMonth(Number(month))
        setShowYearlyOverview(false)
    }

    const shiftMonth = (direction) => {
        const sorted = availableMonths
            .filter(item => item && item.year && item.month)
            .map(item => ({ year: Number(item.year), month: Number(item.month) }))
            .sort((a, b) => (a.year - b.year) || (a.month - b.month))

        if (sorted.length > 0) {
            const currentIndex = sorted.findIndex(item => item.year === viewYear && item.month === viewMonth)
            if (currentIndex >= 0) {
                const next = sorted[currentIndex + direction]
                if (next) {
                    handleMonthSelect(next.year, next.month)
                    return
                }
            }
        }

        const nextMonth = viewMonth + direction
        if (nextMonth < 1) {
            handleMonthSelect(viewYear - 1, 12)
        } else if (nextMonth > 12) {
            handleMonthSelect(viewYear + 1, 1)
        } else {
            handleMonthSelect(viewYear, nextMonth)
        }
    }

    const visibleDays = useMemo(() => {
        return allDays
            .filter(day => day && day.year_num === viewYear && day.month_num === viewMonth)
            .sort((a, b) => getDayNumber(a) - getDayNumber(b))
    }, [allDays, viewYear, viewMonth])

    const monthCells = useMemo(() => {
        const firstDay = visibleDays[0]
        const leadingBlankCount = getMondayFirstOffset(firstDay?.date_str)
        return [...Array.from({ length: leadingBlankCount }, () => null), ...visibleDays]
    }, [visibleDays])

    const visibleTrainingDays = visibleDays.filter(day => day && !day.is_rest).length

    const tierCounts = useMemo(() => {
        const counts = {
            action_library: 0,
            kb_fallback: 0,
            plan_only: 0,
            needs_evidence: 0,
        }
        for (const key of Object.keys(counts)) {
            counts[key] = visibleDays.filter(day => day?.evidence_tier === key).length
        }
        if (visibleDays.length === 0) {
            for (const key of Object.keys(counts)) {
                counts[key] = Number(evidenceSummary[key] || 0)
            }
        }
        return counts
    }, [evidenceSummary, visibleDays])

    const startWeek = p.start_week_index ?? 1
    const endWeek = p.end_week_index ?? 1
    const currentMonthAvailable = availableMonthKeys.size === 0 || availableMonthKeys.has(getMonthKey(viewYear, viewMonth))

    const yearOptions = useMemo(() => {
        const yearsFromAvailable = availableMonths.map(item => Number(item.year)).filter(Boolean)
        const baseYears = yearsFromAvailable.length > 0 ? yearsFromAvailable : [Number(p.year || viewYear || 2026)]
        const minYear = Math.min(...baseYears, viewYear) - 1
        const maxYear = Math.max(...baseYears, viewYear) + 1
        const years = []
        for (let year = minYear; year <= maxYear; year++) years.push(year)
        return years
    }, [availableMonths, p.year, viewYear])

    return (
        <Card className="mb-4 rounded-lg p-4 shadow-sm sm:p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 flex-wrap items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => shiftMonth(-1)} className="h-7 w-7 p-0" aria-label="上个月">
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Calendar className="ml-1 h-4 w-4 text-primary" />
                    <select
                        value={viewYear}
                        onChange={(event) => setViewYear(Number(event.target.value))}
                        className="cursor-pointer rounded border border-border bg-transparent px-1 py-0.5 text-sm font-medium"
                    >
                        {yearOptions.map(year => (
                            <option key={year} value={year}>{year}年</option>
                        ))}
                    </select>
                    <select
                        value={viewMonth}
                        onChange={(event) => setViewMonth(Number(event.target.value))}
                        className="cursor-pointer rounded border border-border bg-transparent px-1 py-0.5 text-sm font-medium"
                    >
                        {MONTH_NAMES.map((name, idx) => {
                            const month = idx + 1
                            const disabled = availableMonthKeys.size > 0 && !availableMonthKeys.has(getMonthKey(viewYear, month))
                            return (
                                <option key={month} value={month} disabled={disabled}>{name}</option>
                            )
                        })}
                    </select>
                    <Button variant="ghost" size="sm" onClick={() => shiftMonth(1)} className="h-7 w-7 p-0" aria-label="下个月">
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>

                <div className="flex flex-wrap items-center justify-end gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        className="gap-1 text-xs"
                        onClick={() => setShowYearlyOverview(!showYearlyOverview)}
                    >
                        <LayoutGrid className="h-3.5 w-3.5" />
                        {showYearlyOverview ? "收起概览" : "年度概览"}
                    </Button>
                    <span className="text-xs text-muted-foreground">
                        第 {startWeek}-{endWeek} 周
                    </span>
                </div>
            </div>

            {showYearlyOverview && (
                <div className="mb-4">
                    <YearlyOverview
                        monthSummaries={monthSummaries}
                        onSelectMonth={handleMonthSelect}
                    />
                </div>
            )}

            {phases.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                    {phases.map((phase, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                            {phase.phase}：第 {phase.start_week}-{phase.end_week} 周
                        </Badge>
                    ))}
                </div>
            )}

            <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" /> 动作库课表 {tierCounts.action_library || ""}
                </span>
                <span className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-amber-400" /> 参考生成 {tierCounts.kb_fallback || ""}
                </span>
                <span className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-gray-300" /> 基础计划 {tierCounts.plan_only || ""}
                </span>
                {tierCounts.needs_evidence > 0 && (
                    <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-rose-400" /> 待补证据 {tierCounts.needs_evidence}
                    </span>
                )}
                <span className="w-full sm:ml-auto sm:w-auto">
                    {viewYear}年{viewMonth}月 · 共 {visibleTrainingDays} 个训练日
                </span>
            </div>

            <div className="w-full overflow-x-auto">
                <div className="min-w-[620px]">
                    <div className="mb-1 grid grid-cols-7 gap-1">
                        {DAY_NAMES.map(dayName => (
                            <div key={dayName} className="py-1 text-center text-xs font-medium text-muted-foreground">
                                {dayName}
                            </div>
                        ))}
                    </div>

                    <div className="grid grid-cols-7 gap-1">
                        {monthCells.map((day, idx) => (
                            <CalendarDayCell
                                key={day ? `${day.year_num || ""}-${day.month_num || ""}-${day.date_str || day.day_label || idx}` : `blank-${idx}`}
                                day={day}
                                onClick={handleDayClick}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {visibleDays.length === 0 && (
                <p className="mt-3 text-center text-xs text-muted-foreground">
                    {currentMonthAvailable
                        ? `${viewYear}年${viewMonth}月暂无训练安排。`
                        : `${viewYear}年${viewMonth}月不在当前计划范围内，请切换可用月份查看。`}
                </p>
            )}

            <p className="mt-3 text-center text-xs text-muted-foreground">
                点击日期查看课表详情；强度按 Z1-Z9 执行。
            </p>

            <DayDetailSheet
                day={selectedDay}
                open={sheetOpen}
                onOpenChange={setSheetOpen}
                evidenceTierMap={evidenceTierMap}
            />
        </Card>
    )
}
