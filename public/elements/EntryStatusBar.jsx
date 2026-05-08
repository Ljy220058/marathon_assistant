import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Activity, Target, TrendingUp } from "lucide-react"

const LOAD_COLORS = {
    "恢复": "bg-blue-500",
    "减量": "bg-gray-400",
    "低": "bg-green-500",
    "中": "bg-yellow-500",
    "高": "bg-orange-500",
    "比赛": "bg-red-500",
}

export default function EntryStatusBar() {
    const p = props || {}
    const weekIndex = p.week_index ?? 1
    const totalWeeks = p.total_weeks ?? 4
    const phase = p.phase || "\u8BAD\u7EC3\u671F"
    const loadLevel = p.load_level || "\u2014"
    const dayLabel = p.day_label || "\u5F53\u524D"
    const trainingType = p.training_type || "\u5F85\u67E5\u770B"
    const mainSet = p.main_set || "\u67E5\u770B\u672C\u5468\u5361\u7247"
    const totalKm = Number(p.total_km || 0)
    const trainingDayCount = p.training_day_count ?? 0
    const weekGoal = p.week_goal || ""

    const loadBadgeColor = LOAD_COLORS[loadLevel] || "bg-gray-400"

    return (
        <Card className="p-4 sm:p-5 mb-4 border-l-4 border-l-primary rounded-lg shadow-sm">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Activity className="w-5 h-5 text-primary" />
                    <span className="font-semibold text-base">训练入口状态</span>
                </div>
                <Badge variant="outline" className={`${loadBadgeColor} text-white text-xs px-2`}>
                    {loadLevel}
                </Badge>
            </div>

            <div className="mb-3">
                <span className="text-sm font-medium">
                    第 {weekIndex} / {totalWeeks} 周
                </span>
                <span className="text-muted-foreground text-sm ml-2">· {phase}</span>
            </div>

            <div className="p-3 mb-3 rounded-md bg-muted/30">
                <div className="flex items-center gap-2 mb-1">
                    <Target className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium">当前建议</span>
                </div>
                <div className="text-sm ml-6">
                    {dayLabel}：{trainingType}{totalKm > 0 ? ` · ${totalKm.toFixed(1)}km` : ""} · {mainSet}
                </div>
            </div>

            <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">
                    本周：{trainingDayCount} 个训练日
                    {weekGoal ? ` · ${weekGoal}` : ""}
                </span>
            </div>

            <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">周进度</span>
                <Progress value={0} className="h-2 flex-1" />
                <span className="text-xs text-muted-foreground">0/{trainingDayCount}</span>
            </div>

            <p className="text-xs text-muted-foreground mt-3">
                优先看当前周摘要；需要时再展开每日详情、解释和证据。
            </p>
        </Card>
    )
}
