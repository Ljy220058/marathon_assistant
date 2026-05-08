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
    "action_library": "bg-emerald-500/10 text-emerald-500 border-emerald-500/30",
    "kb_fallback": "bg-amber-500/10 text-amber-500 border-amber-500/30",
    "plan_only": "bg-gray-400/10 text-gray-400 border-gray-400/30",
}

const ZONE_COLORS = {
    "Z1": "bg-blue-200/10 text-blue-600",
    "Z2": "bg-green-200/10 text-green-600",
    "Z3": "bg-green-400/10 text-green-700",
    "Z4": "bg-yellow-300/10 text-yellow-700",
    "Z5": "bg-orange-300/10 text-orange-700",
    "Z6": "bg-orange-500/10 text-orange-600",
    "Z7": "bg-red-400/10 text-red-600",
    "Z8": "bg-red-500/10 text-red-700",
    "Z9": "bg-purple-500/10 text-purple-700",
}

function getZoneColor(zoneRange) {
    if (!zoneRange) return "bg-muted/10 text-muted-foreground"
    const zones = zoneRange.replace(/→/g, "-").split("-")
    for (const z of zones) {
        const zNum = z.trim()
        if (ZONE_COLORS[zNum]) return ZONE_COLORS[zNum]
    }
    return "bg-muted/10 text-muted-foreground"
}

function getTrainingBadge(trainingType) {
    return TRAINING_BADGES[trainingType] || "bg-primary/10 text-primary border-primary/20"
}

function CalendarDayCell({ day, onClick }) {
    if (!day) return <div className="min-h-24" />

    const isRest = day.is_rest
    const trainingBadge = isRest
        ? getTrainingBadge("休息")
        : getTrainingBadge(day.training_type)
    const zoneLabel = day.zone_range || ""
    const trainingLabel = day.training_type_label || day.training_type || (isRest ? "休息" : "未安排")

    return (
        <div
            className={`min-h-24 p-2 border rounded-md cursor-pointer hover:bg-muted/30 transition-colors flex flex-col gap-1 ${isRest ? 'opacity-60' : ''}`}
            onClick={() => onClick(day)}
        >
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">{day.day_label}</span>
                <span className={`w-1.5 h-1.5 rounded-full ${day.evidence_tier === 'action_library' ? 'bg-emerald-400' : day.evidence_tier === 'kb_fallback' ? 'bg-amber-400' : 'bg-gray-300'}`} />
            </div>
            <div className="min-h-0 flex-1 flex flex-col justify-center">
                <Badge variant="outline" className={`max-w-full truncate text-[10px] px-1 py-0 leading-tight ${trainingBadge}`}>
                    {trainingLabel}
                </Badge>
            </div>
            {!isRest && zoneLabel && (
                <div className="flex min-w-0 items-center gap-1">
                    <Heart className="w-2.5 h-2.5 text-red-400 shrink-0" />
                    <span className="truncate text-[10px] text-muted-foreground">{zoneLabel}</span>
                </div>
            )}
            {isRest && (
                <span className="text-[10px] text-muted-foreground">恢复日</span>
            )}
        </div>
    )
}

function DayDetailSheet({ day, open, onClose }) {
    if (!day) return null

    const isRest = day.is_rest

    return (
        <Sheet open={open} onOpenChange={onClose}>
            <SheetContent side="right" className="w-[90vw] max-w-[540px] sm:w-[540px] overflow-y-auto">
                <SheetHeader>
                    <SheetTitle>{day.date_str || `${day.day_label} 课表详情`}</SheetTitle>
                    <SheetDescription>
                        第 {day.week_index} 周 · {day.day_label}
                    </SheetDescription>
                </SheetHeader>

                <div className="mt-6 space-y-4">
                    <div className="flex gap-2 flex-wrap">
                        <Badge variant="outline" className={`text-xs ${getTrainingBadge(day.training_type)}`}>
                            {day.training_type_label || day.training_type || (isRest ? "休息" : "")}
                        </Badge>
                        {!isRest && day.zone_range && (
                            <Badge variant="outline" className={`text-xs ${getZoneColor(day.zone_range)}`}>
                                强度：{day.intensity_target || day.zone_range}
                            </Badge>
                        )}
                        <Badge variant="outline" className={`text-xs ${EVIDENCE_TIER_BADGES[day.evidence_tier] || ''}`}>
                            {day.evidence_tier_label || "基础计划"}
                        </Badge>
                    </div>

                    {isRest && (
                        <Card className="p-3 bg-muted/20">
                            <div className="flex items-start gap-2">
                                <Info className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                                <p className="text-sm text-muted-foreground">
                                    {day.training_objective || "休息日，建议充分恢复。可进行轻度交叉训练或拉伸。"}
                                </p>
                            </div>
                        </Card>
                    )}

                    {!isRest && (
                        <>
                            {day.training_objective && (
                                <Card className="p-3 bg-muted/20">
                                    <div className="flex items-center gap-2 mb-1">
                                        <Lightbulb className="w-4 h-4 text-amber-500" />
                                        <span className="text-sm font-medium">训练目标</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground">{day.training_objective}</p>
                                </Card>
                            )}

                            {day.warmup && (
                                <div className="flex items-start gap-2">
                                    <Zap className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                                    <div className="text-sm">
                                        <span className="font-medium">热身：</span>
                                        {day.warmup}
                                    </div>
                                </div>
                            )}

                            {day.main_set && (
                                <div className="flex items-start gap-2">
                                    <Flame className="w-4 h-4 text-orange-500 mt-0.5 shrink-0" />
                                    <div className="text-sm">
                                        <span className="font-medium">主课：</span>
                                        {day.main_set}
                                    </div>
                                </div>
                            )}

                            {day.cooldown && (
                                <div className="flex items-start gap-2">
                                    <Timer className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                                    <div className="text-sm">
                                        <span className="font-medium">放松：</span>
                                        {day.cooldown}
                                    </div>
                                </div>
                            )}

                            {day.alternative && (
                                <div className="flex items-start gap-2">
                                    <Shield className="w-4 h-4 text-indigo-500 mt-0.5 shrink-0" />
                                    <div className="text-sm">
                                        <span className="font-medium">替代训练：</span>
                                        {day.alternative}
                                    </div>
                                </div>
                            )}

                            {!day.intensity_target && day.zone_label && (
                                <div className="flex items-start gap-2">
                                    <Heart className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                                    <div className="text-sm">
                                        <span className="font-medium">建议区间：</span>
                                        {day.zone_label}
                                    </div>
                                </div>
                            )}
                        </>
                    )}

                    <Separator />

                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <Bookmark className="w-4 h-4 text-primary" />
                            <span className="text-sm font-medium">证据状态</span>
                        </div>
                        <Card className="p-3 bg-muted/20">
                            <div className="flex items-center gap-2 mb-1">
                                <Badge variant="outline" className={`text-xs ${EVIDENCE_TIER_BADGES[day.evidence_tier] || ''}`}>
                                    {day.evidence_tier_label || "基础计划"}
                                </Badge>
                            </div>
                            {day.evidence_tier === "action_library" && (
                                <p className="text-xs text-muted-foreground">
                                    课表数据来自动作库直接证据，训练方案经过验证。
                                </p>
                            )}
                            {day.evidence_tier === "kb_fallback" && (
                                <p className="text-xs text-muted-foreground">
                                    动作库中未找到该训练类型的直接证据，已基于其他知识库内容生成参考课表。训练方案为通用原则推导，建议结合个人体感调整。
                                </p>
                            )}
                            {day.evidence_tier === "plan_only" && (
                                <p className="text-xs text-muted-foreground">
                                    当前训练类型在知识库中暂无充分证据支撑。训练安排基于训练计划骨架，建议后续补充动作库或训练数据以获得更精准的课表。
                                </p>
                            )}
                            {day.source && day.source.length > 0 && (
                                <div className="mt-2">
                                    <p className="text-xs font-medium text-muted-foreground mb-1">信息来源：</p>
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
                        <Card className="p-3 bg-muted/10">
                            <div className="flex items-start gap-2">
                                <Info className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                                <p className="text-xs text-muted-foreground">
                                    该训练日暂无详细训练解释。
                                </p>
                            </div>
                        </Card>
                    )}

                    {day.notes && (
                        <div className="flex items-start gap-2">
                            <StickyNote className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
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
                    <Bookmark className="w-4 h-4" />
                    📖 查看训练解释
                    <span className="ml-auto text-xs text-muted-foreground">
                        {expanded ? "收起 ▲" : "展开 ▼"}
                    </span>
                </Button>

                {expanded && (
                    <Card className="mt-2 p-4 bg-muted/10 space-y-3">
                        {explanation.why_scheduled && explanation.why_scheduled !== "—" && (
                            <div>
                                <div className="flex items-center gap-1.5 mb-1">
                                    <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                                    <span className="text-xs font-semibold">为什么安排</span>
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    {explanation.why_scheduled}
                                    {explanation.evidence_ids && explanation.evidence_ids.length > 0 && (
                                        <span className="ml-1 text-blue-500">
                                            {explanation.evidence_ids.map(id => `\`[${id}]\``).join(" ")}
                                        </span>
                                    )}
                                </p>
                            </div>
                        )}

                        {explanation.primary_target && explanation.primary_target !== "—" && (
                            <div>
                                <div className="flex items-center gap-1.5 mb-1">
                                    <Flame className="w-3.5 h-3.5 text-orange-500" />
                                    <span className="text-xs font-semibold">主要训练目标</span>
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    {explanation.primary_target}
                                </p>
                            </div>
                        )}

                        {explanation.risk_alert && explanation.risk_alert !== "—" && (
                            <div>
                                <div className="flex items-center gap-1.5 mb-1">
                                    <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                                    <span className="text-xs font-semibold">风险提醒</span>
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    {explanation.risk_alert}
                                </p>
                            </div>
                        )}

                        {explanation.alternative_workout && explanation.alternative_workout !== "—" && (
                            <div>
                                <div className="flex items-center gap-1.5 mb-1">
                                    <Shield className="w-3.5 h-3.5 text-indigo-500" />
                                    <span className="text-xs font-semibold">状态不佳时替代</span>
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    {explanation.alternative_workout}
                                </p>
                            </div>
                        )}

                        {explanation.target_labels && explanation.target_labels.length > 0 && (
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs text-muted-foreground">目标标签：</span>
                                {explanation.target_labels.map((label, idx) => (
                                    <Badge key={idx} variant="secondary" className="text-[10px]">
                                        {label}
                                    </Badge>
                                ))}
                            </div>
                        )}

                        {explanation.decision_summary && explanation.decision_summary !== "—" && (
                            <div>
                                <div className="flex items-center gap-1.5 mb-1">
                                    <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                                    <span className="text-xs font-semibold">决策摘要</span>
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    {explanation.decision_summary}
                                </p>
                            </div>
                        )}

                        {explanation.explanation_source && explanation.explanation_source !== "—" && (
                            <div className="flex items-center gap-1.5">
                                <Info className="w-3 h-3 text-muted-foreground" />
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
                <p className="text-xs text-muted-foreground text-center">暂无年度训练数据</p>
            </Card>
        )
    }

    return (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {monthSummaries.map((ms, idx) => {
                const hasDays = ms.total_days > 0
                return (
                    <Card
                        key={idx}
                        className={`p-3 cursor-pointer hover:bg-muted/30 transition-colors ${!hasDays ? 'opacity-40' : ''}`}
                        onClick={() => hasDays && onSelectMonth(ms.year, ms.month)}
                    >
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium">
                                {ms.year}年{MONTH_NAMES[ms.month - 1]}
                            </span>
                            <Badge variant="secondary" className="text-[10px]">
                                {ms.total_days}天
                            </Badge>
                        </div>
                        {hasDays && (
                            <div className="flex gap-0.5 mt-1">
                                {ms.action_library > 0 && (
                                    <div className="flex-1 h-1 bg-emerald-400 rounded" title={`动作库：${ms.action_library}天`} />
                                )}
                                {ms.kb_fallback > 0 && (
                                    <div className="flex-1 h-1 bg-amber-400 rounded" title={`参考生成：${ms.kb_fallback}天`} />
                                )}
                                {ms.plan_only > 0 && (
                                    <div className="flex-1 h-1 bg-gray-300 rounded" title={`基础计划：${ms.plan_only}天`} />
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
    const p = props || {}
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

    const handleDayClick = (day) => {
        setSelectedDay(day)
        setSheetOpen(true)
    }

    const handleMonthSelect = (year, month) => {
        setViewYear(year)
        setViewMonth(month)
        setShowYearlyOverview(false)
    }

    const handlePrevMonth = () => {
        if (viewMonth === 1) {
            setViewYear(viewYear - 1)
            setViewMonth(12)
        } else {
            setViewMonth(viewMonth - 1)
        }
    }

    const handleNextMonth = () => {
        if (viewMonth === 12) {
            setViewYear(viewYear + 1)
            setViewMonth(1)
        } else {
            setViewMonth(viewMonth + 1)
        }
    }

    const visibleDays = useMemo(() => {
        return allDays.filter(
            d => d && d.year_num === viewYear && d.month_num === viewMonth
        )
    }, [allDays, viewYear, viewMonth])

    const visibleTrainingDays = visibleDays.filter(d => d && !d.is_rest).length

    const totalActionLib = useMemo(() => {
        let count = 0
        for (const d of visibleDays) {
            if (d && d.evidence_tier === "action_library") count++
        }
        return count
    }, [visibleDays])

    const totalKbFallback = useMemo(() => {
        let count = 0
        for (const d of visibleDays) {
            if (d && d.evidence_tier === "kb_fallback") count++
        }
        return count
    }, [visibleDays])

    const totalPlanOnly = useMemo(() => {
        let count = 0
        for (const d of visibleDays) {
            if (d && d.evidence_tier === "plan_only") count++
        }
        return count
    }, [visibleDays])

    const startWeek = p.start_week_index ?? 1
    const endWeek = p.end_week_index ?? 1

    const yearOptions = useMemo(() => {
        const minYear = Math.min(viewYear, p.year || 2026) - 3
        const maxYear = Math.max(viewYear, p.year || 2026) + 3
        const years = []
        for (let y = minYear; y <= maxYear; y++) years.push(y)
        return years
    }, [viewYear, p.year])

    return (
        <Card className="p-4 sm:p-5 mb-4 rounded-lg shadow-sm">
            {/* ---- 导航栏 ---- */}
            <div className="flex items-center justify-between mb-3 flex-wrap gap-3">
                <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={handlePrevMonth} className="h-7 w-7 p-0">
                        <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Calendar className="w-4 h-4 text-primary ml-1" />
                    <select
                        value={viewYear}
                        onChange={(e) => setViewYear(Number(e.target.value))}
                        className="text-sm font-medium bg-transparent border border-border rounded px-1 py-0.5 cursor-pointer"
                    >
                        {yearOptions.map(y => (
                            <option key={y} value={y}>{y}年</option>
                        ))}
                    </select>
                    <select
                        value={viewMonth}
                        onChange={(e) => setViewMonth(Number(e.target.value))}
                        className="text-sm font-medium bg-transparent border border-border rounded px-1 py-0.5 cursor-pointer"
                    >
                        {MONTH_NAMES.map((name, idx) => (
                            <option key={idx} value={idx + 1}>{name}</option>
                        ))}
                    </select>
                    <Button variant="ghost" size="sm" onClick={handleNextMonth} className="h-7 w-7 p-0">
                        <ChevronRight className="w-4 h-4" />
                    </Button>
                </div>

                <div className="flex items-center justify-end gap-2 flex-wrap">
                    <Button
                        variant="outline"
                        size="sm"
                        className="gap-1 text-xs"
                        onClick={() => setShowYearlyOverview(!showYearlyOverview)}
                    >
                        <LayoutGrid className="w-3.5 h-3.5" />
                        {showYearlyOverview ? "收起概览" : "年度概览"}
                    </Button>
                    <span className="text-xs text-muted-foreground">
                        第{startWeek}-{endWeek}周
                    </span>
                </div>
            </div>

            {/* ---- 年度概览 ---- */}
            {showYearlyOverview && (
                <div className="mb-4">
                    <YearlyOverview
                        monthSummaries={monthSummaries}
                        onSelectMonth={handleMonthSelect}
                    />
                </div>
            )}

            {/* ---- 证据分层 ---- */}
            {phases.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                    {phases.map((phase, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                            {phase.phase}：第{phase.start_week}-{phase.end_week}周
                        </Badge>
                    ))}
                </div>
            )}

            <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground flex-wrap">
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" /> 动作库课表
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-400" /> 参考生成
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-gray-300" /> 基础计划
                </span>
                <span className="w-full sm:w-auto sm:ml-auto">{viewYear}年{viewMonth}月 · 共 {visibleTrainingDays} 个训练日</span>
            </div>

            {/* ---- 日历网格 ---- */}
            <div className="w-full overflow-x-auto">
                <div className="min-w-[640px]">
                    <div className="mb-1" style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: "0.25rem" }}>
                        {DAY_NAMES.map(dayName => (
                            <div key={dayName} className="text-xs font-medium text-muted-foreground text-center py-1">
                                {dayName}
                            </div>
                        ))}
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: "0.25rem" }}>
                        {visibleDays.map((day, idx) => (
                            <CalendarDayCell
                                key={`${day.year_num || ""}-${day.month_num || ""}-${day.day_label || ""}-${idx}`}
                                day={day}
                                onClick={handleDayClick}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {visibleDays.length === 0 && (
                <p className="text-xs text-muted-foreground mt-3 text-center">
                    {viewYear}年{viewMonth}月暂无训练安排。请切换月份查看。
                </p>
            )}

            <p className="text-xs text-muted-foreground mt-3 text-center">
                点击日期查看课表；强度按 Z1-Z9 执行。
            </p>

            <DayDetailSheet
                day={selectedDay}
                open={sheetOpen}
                onClose={(open) => setSheetOpen(open)}
            />
        </Card>
    )
}
