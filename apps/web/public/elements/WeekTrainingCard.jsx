import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { Separator } from "@/components/ui/separator"
import {
    Calendar, Flame, ChevronRight, TrendingUp, Target,
    AlertCircle, MapPin, StickyNote, Zap, Timer, Heart
} from "lucide-react"
import { useState } from "react"

const TRAINING_BADGES = {
    "\u8F7B\u677E\u8DD1": "bg-green-500/10 text-green-500 border-green-500/20",
    "\u95F4\u6B47\u8DD1": "bg-red-500/10 text-red-500 border-red-500/20",
    "\u8282\u594F\u8DD1": "bg-orange-500/10 text-orange-500 border-orange-500/20",
    "\u957F\u8DDD\u79BB": "bg-blue-500/10 text-blue-500 border-blue-500/20",
    "\u4F11\u606F": "bg-gray-400/10 text-gray-400 border-gray-400/20",
    "\u529B\u91CF": "bg-purple-500/10 text-purple-500 border-purple-500/20",
    "\u6CD5\u7279\u83B1\u514B": "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    "\u6E10\u901F\u8DD1": "bg-cyan-500/10 text-cyan-500 border-cyan-500/20",
    "\u6062\u590D\u8DD1": "bg-teal-500/10 text-teal-500 border-teal-500/20",
    "\u6BD4\u8D5B\u6A21\u62DF": "bg-pink-500/10 text-pink-500 border-pink-500/20",
}

const LOAD_COLORS = {
    "\u6062\u590D": "bg-blue-500",
    "\u51CF\u91CF": "bg-gray-400",
    "\u4F4E": "bg-green-500",
    "\u4E2D": "bg-yellow-500",
    "\u9AD8": "bg-orange-500",
    "\u6BD4\u8D5B": "bg-red-500",
}

function getBadgeClass(trainingType) {
    return TRAINING_BADGES[trainingType] || "bg-primary/10 text-primary border-primary/20"
}

function DayRow({ day, index, defaultExpanded = false }) {
    const [expanded, setExpanded] = useState(Boolean(defaultExpanded))
    if (!day) return null

    const dayLabel = day.day || `Day ${index + 1}`
    const trainingType = day.training_type || "\u672A\u5B89\u6392"
    const isRest = trainingType === "\u4F11\u606F"
    const isKey = day.key_workout

    const warmupKm = Number(day.warmup_km || 0)
    const mainKm = Number(day.main_km || 0)
    const cooldownKm = Number(day.cooldown_km || 0)
    const totalKm = warmupKm + mainKm + cooldownKm

    const hrZone = day.heart_rate_zone || ""
    const zoneRange = day.zone_range || ""
    const zoneLabel = day.zone_label || ""
    const intensityTarget = day.intensity_target || ""
    const pace = day.pace_range || ""
    const venue = day.venue || ""
    const notes = day.notes || ""
    const warmup = day.warmup || ""
    const mainSet = day.main_set || ""
    const cooldown = day.cooldown || ""

    const zoneDisplay = zoneLabel || intensityTarget || zoneRange || ""
    const badgeClass = isRest ? getBadgeClass("\u4F11\u606F") : getBadgeClass(trainingType)

    return (
        <div>
            <div
                className={`flex min-w-0 items-center gap-2 py-2 px-3 rounded-md cursor-pointer hover:bg-muted/50 transition-colors ${isKey ? 'border-l-2 border-l-orange-500' : ''}`}
                onClick={() => setExpanded(!expanded)}
            >
                {isKey && <Flame className="w-4 h-4 text-orange-500 shrink-0" />}
                <span className="text-sm font-medium w-12 shrink-0">{dayLabel}</span>
                <Badge variant="outline" className={`max-w-[7rem] truncate text-xs shrink-0 ${badgeClass}`}>
                    {trainingType}
                </Badge>
                {!isRest && (
                    <span className="min-w-0 truncate text-right text-xs text-muted-foreground ml-auto">
                        {totalKm > 0 ? `${totalKm.toFixed(1)}km` : ""}
                        {zoneDisplay ? ` · ${zoneDisplay}` : (hrZone ? ` · ${hrZone}` : "")}
                        {!zoneDisplay && pace ? ` · ${pace}` : ""}
                    </span>
                )}
                {isRest && <span className="text-xs text-muted-foreground ml-auto">恢复日</span>}
                <ChevronRight className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`} />
            </div>

            {expanded && !isRest && (
                <div className="mx-3 my-2 rounded-md border border-border/60 p-3 bg-muted/20">
                    {warmup && (
                        <div className="flex items-start gap-2 mb-2">
                            <Zap className="w-3.5 h-3.5 text-green-500 mt-0.5 shrink-0" />
                            <div className="text-xs">
                                <span className="font-medium">热身：</span>
                                {warmup}{warmupKm > 0 ? ` (${warmupKm.toFixed(1)}km)` : ""}
                            </div>
                        </div>
                    )}
                    {mainSet && (
                        <div className="flex items-start gap-2 mb-2">
                            <Flame className="w-3.5 h-3.5 text-orange-500 mt-0.5 shrink-0" />
                            <div className="text-xs">
                                <span className="font-medium">主课：</span>
                                {mainSet}{mainKm > 0 ? ` (${mainKm.toFixed(1)}km)` : ""}
                            </div>
                        </div>
                    )}
                    {cooldown && (
                        <div className="flex items-start gap-2 mb-2">
                            <Timer className="w-3.5 h-3.5 text-blue-500 mt-0.5 shrink-0" />
                            <div className="text-xs">
                                <span className="font-medium">放松：</span>
                                {cooldown}{cooldownKm > 0 ? ` (${cooldownKm.toFixed(1)}km)` : ""}
                            </div>
                        </div>
                    )}
                    {(hrZone || zoneDisplay) && (
                        <div className="flex items-start gap-2 mb-2">
                            <Heart className="w-3.5 h-3.5 text-red-500 mt-0.5 shrink-0" />
                            <div className="text-xs">
                                <span className="font-medium">强度区间：</span>
                                {zoneDisplay || hrZone}
                                {!zoneDisplay && pace ? ` · 配速 ${pace}` : ""}
                            </div>
                        </div>
                    )}
                    {venue && (
                        <div className="flex items-start gap-2 mb-2">
                            <MapPin className="w-3.5 h-3.5 text-muted-foreground mt-0.5 shrink-0" />
                            <div className="text-xs text-muted-foreground">{venue}</div>
                        </div>
                    )}
                    {notes && (
                        <div className="flex items-start gap-2">
                            <StickyNote className="w-3.5 h-3.5 text-muted-foreground mt-0.5 shrink-0" />
                            <div className="text-xs text-muted-foreground">{notes}</div>
                        </div>
                    )}
                </div>
            )}

            {expanded && isRest && (
                <div className="mx-3 my-2 rounded-md border border-border/60 p-3 bg-muted/20">
                    <div className="text-xs text-muted-foreground">
                        休息日，建议充分恢复。可进行轻度交叉训练或拉伸。
                    </div>
                </div>
            )}
        </div>
    )
}

export default function WeekTrainingCard() {
    const p = props || {}
    const weekIndex = p.week_index ?? 1
    const phase = p.phase || "\u8BAD\u7EC3\u671F"
    const loadLevel = p.load_level || "\u2014"
    const weekGoal = p.week_goal || ""
    const loadProgression = p.load_progression_note || ""
    const days = Array.isArray(p.days) ? p.days : []
    const keyWorkouts = Array.isArray(p.key_workouts) ? p.key_workouts : []
    const actionSuggestions = Array.isArray(p.action_suggestions) ? p.action_suggestions : []
    const executionReminder = p.execution_reminder || ""
    const otherWeeks = Array.isArray(p.other_weeks) ? p.other_weeks : []
    const defaultExpandedDayIndexes = Array.isArray(p.default_expanded_day_indexes) ? p.default_expanded_day_indexes : []

    const loadBadgeColor = LOAD_COLORS[loadLevel] || "bg-gray-400"

    return (
        <Card id={`week-${weekIndex}`} className="p-4 sm:p-5 mb-4 rounded-lg shadow-sm scroll-mt-4">
            <div className="flex items-start justify-between mb-3 flex-wrap gap-3">
                <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-primary" />
                    <span className="font-semibold text-base">
                        第 {weekIndex} 周计划
                    </span>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                    {loadLevel && (
                        <Badge variant="outline" className={`${loadBadgeColor} text-white text-xs px-2`}>
                            {loadLevel}
                        </Badge>
                    )}
                    <Badge variant="secondary" className="text-xs">{phase}</Badge>
                </div>
            </div>

            {weekGoal && (
                <div className="flex items-start gap-2 mb-3">
                    <Target className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                    <p className="text-sm">{weekGoal}</p>
                </div>
            )}

            {loadProgression && (
                <div className="flex items-start gap-2 mb-3">
                    <TrendingUp className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                    <p className="text-xs text-muted-foreground">{loadProgression}</p>
                </div>
            )}

            <Separator className="my-3" />

            <div className="space-y-0">
                <p className="text-xs font-medium text-muted-foreground mb-2 px-1">7 天缩略行</p>
                {days.map((day, idx) => (
                    <DayRow
                        key={idx}
                        day={day}
                        index={idx}
                        defaultExpanded={defaultExpandedDayIndexes.includes(idx + 1)}
                    />
                ))}
            </div>

            {keyWorkouts.length > 0 && (
                <div className="mt-3 pt-3 border-t">
                    <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                        <Flame className="w-3.5 h-3.5 text-orange-500" /> 本周关键训练
                    </p>
                    <div className="flex flex-wrap gap-1">
                        {keyWorkouts.map((kw, idx) => (
                            <Badge key={idx} variant="outline" className="text-xs border-orange-500/30 text-orange-500">
                                {kw}
                            </Badge>
                        ))}
                    </div>
                </div>
            )}

            {actionSuggestions.length > 0 && (
                <div className="mt-3">
                    <p className="text-xs font-medium text-muted-foreground mb-1">行动建议</p>
                    <ul className="text-xs text-muted-foreground space-y-0.5 list-disc list-inside">
                        {actionSuggestions.slice(0, 3).map((s, idx) => (
                            <li key={idx}>{s}</li>
                        ))}
                    </ul>
                </div>
            )}

            {executionReminder && (
                <div className="mt-3 flex items-start gap-2">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                    <p className="text-xs text-muted-foreground">{executionReminder}</p>
                </div>
            )}

            {otherWeeks.length > 0 && (
                <div className="mt-4">
                    <Accordion type="single" collapsible>
                        <AccordionItem value="other-weeks" className="border-none">
                            <AccordionTrigger className="text-xs font-medium text-muted-foreground py-1 hover:no-underline">
                                查看其他周摘要 ({otherWeeks.length} 周)
                            </AccordionTrigger>
                            <AccordionContent>
                                <div className="space-y-2 pt-2">
                                    {otherWeeks.map((week, idx) => (
                                        <Card key={idx} className="p-2 bg-muted/20">
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-medium">
                                                    第 {week.week_index ?? '?'} 周
                                                </span>
                                                <span className="text-xs text-muted-foreground">
                                                    {week.phase || ''}{week.load_level ? ` · ${week.load_level}` : ''}
                                                </span>
                                            </div>
                                            {week.week_goal && (
                                                <p className="text-xs text-muted-foreground mt-1">{week.week_goal}</p>
                                            )}
                                        </Card>
                                    ))}
                                </div>
                            </AccordionContent>
                        </AccordionItem>
                    </Accordion>
                </div>
            )}

            <p className="text-xs text-muted-foreground mt-3">
                点击某一天可展开当日详情。
            </p>
        </Card>
    )
}
