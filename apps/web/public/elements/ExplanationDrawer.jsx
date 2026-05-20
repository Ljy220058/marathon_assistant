import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import {
    HelpCircle, AlertTriangle, Lightbulb, FileText,
    Bookmark, ChevronRight, Shield, BarChart3
} from "lucide-react"
import { useState } from "react"

function getRiskColor(level) {
    if (!level) return "text-muted-foreground"
    const l = level.toLowerCase()
    if (l.includes("高") || l.includes("严重")) return "text-red-500"
    if (l.includes("中")) return "text-amber-500"
    if (l.includes("低")) return "text-yellow-500"
    return "text-muted-foreground"
}

function getRiskBg(level) {
    if (!level) return "bg-muted/20"
    const l = level.toLowerCase()
    if (l.includes("高") || l.includes("严重")) return "bg-red-500/10"
    if (l.includes("中")) return "bg-amber-500/10"
    if (l.includes("低")) return "bg-yellow-500/10"
    return "bg-muted/20"
}

export default function ExplanationDrawer() {
    const p = props || {}
    const [open, setOpen] = useState(false)

    const day = p.day || ""
    const phase = p.phase || ""
    const whyScheduled = p.why_scheduled || "\u6682\u65E0\u8BE6\u7EC6\u8BF4\u660E"
    const primaryTarget = p.primary_target || "\u6682\u65E0"
    const riskAlert = p.risk_alert || ""
    const alternativeWorkout = p.alternative_workout || ""
    const decisionSummary = p.decision_summary || ""
    const evidenceIds = Array.isArray(p.evidence_ids) ? p.evidence_ids : []
    const detailLines = Array.isArray(p.detail_lines) ? p.detail_lines : []
    const summary = p.summary || ""
    const coverageRatio = p.coverage_ratio ?? 0

    return (
        <Card className="p-4 mb-4 border-l-4 border-l-primary rounded-lg shadow-sm">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <HelpCircle className="w-5 h-5 text-primary" />
                    <span className="font-semibold text-base">关键训练解释</span>
                </div>
                {coverageRatio > 0 && (
                    <Badge variant="secondary" className="text-xs">
                        覆盖率 {coverageRatio}%
                    </Badge>
                )}
            </div>

            {day && phase && (
                <p className="text-xs text-muted-foreground mt-1">
                    {day} · {phase}
                </p>
            )}

            <div className="mt-3 space-y-2">
                {whyScheduled && (
                    <div className="flex items-start gap-2">
                        <Lightbulb className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                        <div className="text-sm">
                            <span className="font-medium">为什么安排：</span>
                            {whyScheduled}
                        </div>
                    </div>
                )}

                {primaryTarget && (
                    <div className="flex items-start gap-2">
                        <BarChart3 className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                        <div className="text-sm">
                            <span className="font-medium">主要提升：</span>
                            {primaryTarget}
                        </div>
                    </div>
                )}

                {riskAlert && (
                    <div className={`flex items-start gap-2 p-2 rounded ${getRiskBg(riskAlert)}`}>
                        <AlertTriangle className={`w-4 h-4 ${getRiskColor(riskAlert)} mt-0.5 shrink-0`} />
                        <div className="text-sm">
                            <span className="font-medium">需要注意：</span>
                            <span className={getRiskColor(riskAlert)}>{riskAlert}</span>
                        </div>
                    </div>
                )}

                {alternativeWorkout && (
                    <div className="flex items-start gap-2">
                        <Shield className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                        <div className="text-sm">
                            <span className="font-medium">状态不佳时替代：</span>
                            {alternativeWorkout}
                        </div>
                    </div>
                )}
            </div>

            <Separator className="my-3" />

            <Sheet open={open} onOpenChange={setOpen}>
                <SheetTrigger asChild>
                    <Button variant="outline" size="sm" className="w-full min-w-0 justify-start">
                        <FileText className="w-4 h-4 mr-2" />
                        <span className="truncate">打开解释抽屉：决策细节与证据</span>
                        <ChevronRight className="w-4 h-4 ml-auto" />
                    </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-[90vw] max-w-[540px] sm:w-[540px] overflow-y-auto">
                    <SheetHeader>
                        <SheetTitle>训练解释详情</SheetTitle>
                        <SheetDescription>
                            {day}{phase ? ` · ${phase}` : ''}
                        </SheetDescription>
                    </SheetHeader>

                    <div className="mt-6 space-y-4">
                        {summary && (
                            <div className="text-sm text-muted-foreground">
                                {summary}
                            </div>
                        )}

                        {decisionSummary && (
                            <Card className="p-3 bg-muted/20">
                                <div className="flex items-center gap-2 mb-1">
                                    <Bookmark className="w-4 h-4 text-primary" />
                                    <span className="text-sm font-medium">决策摘要</span>
                                </div>
                                <p className="text-xs text-muted-foreground">{decisionSummary}</p>
                            </Card>
                        )}

                        {detailLines.length > 0 && (
                            <Accordion type="single" collapsible>
                                <AccordionItem value="details" className="border-none">
                                    <AccordionTrigger className="text-sm font-medium py-2 hover:no-underline">
                                        技术细节与约束检查
                                    </AccordionTrigger>
                                    <AccordionContent>
                                        <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                                            {detailLines.map((line, idx) => (
                                                <li key={idx}>{line}</li>
                                            ))}
                                        </ul>
                                    </AccordionContent>
                                </AccordionItem>
                            </Accordion>
                        )}

                        {evidenceIds.length > 0 && (
                            <div>
                                <p className="text-xs font-medium text-muted-foreground mb-2">关联证据</p>
                                <div className="flex flex-wrap gap-1">
                                    {evidenceIds.map((evId, idx) => (
                                        <Badge key={idx} variant="outline" className="text-xs font-mono">
                                            [{evId}]
                                        </Badge>
                                    ))}
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    可在&ldquo;参考来源 / 查看证据（同号按钮）&rdquo;中点击同编号按钮打开原文。
                                </p>
                            </div>
                        )}
                    </div>
                </SheetContent>
            </Sheet>

            {summary && (
                <p className="text-xs text-muted-foreground mt-2">{summary}</p>
            )}
        </Card>
    )
}
