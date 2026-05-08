import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

function ActionItem({ item }) {
    const handleClick = async () => {
        if (!item || !item.name) return
        await callAction({
            name: item.name,
            payload: item.payload || {},
        })
    }

    return (
        <Button
            variant="ghost"
            className="h-auto w-full justify-start rounded-lg border border-border/60 bg-background/70 p-3 text-left hover:bg-primary/10 hover:text-primary"
            onClick={handleClick}
        >
            <div className="flex w-full items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-base">
                    {item.icon || "•"}
                </div>
                <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-semibold leading-5">
                        {item.label || item.name}
                    </div>
                    {item.description && (
                        <div className="mt-0.5 line-clamp-2 whitespace-normal text-xs leading-4 text-muted-foreground">
                            {item.description}
                        </div>
                    )}
                </div>
            </div>
        </Button>
    )
}

function ActionGroup({ group }) {
    const items = Array.isArray(group?.items) ? group.items : []
    if (!items.length) return null

    return (
        <Card className="rounded-lg border border-border/70 bg-card/90 p-3 shadow-sm">
            <div className="mb-2 flex items-center justify-between px-1">
                <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {group.title || "操作"}
                </div>
                <Badge variant="outline" className="h-5 px-1.5 text-[10px]">
                    {items.length}
                </Badge>
            </div>
            <div className="space-y-2">
                {items.map((item, index) => (
                    <ActionItem key={`${item.name || "action"}-${index}`} item={item} />
                ))}
            </div>
        </Card>
    )
}

export default function LeftActionRail() {
    const p = props || {}
    const groups = Array.isArray(p.groups) ? p.groups : []

    return (
        <div className="mb-4 grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
            <aside className="order-2 space-y-3 lg:order-1">
                <Card className="rounded-lg border border-primary/20 bg-primary/5 p-3">
                    <div className="text-sm font-semibold">左侧操作栏</div>
                    <div className="mt-1 text-xs leading-5 text-muted-foreground">
                        常用入口已按训练计划、知识库和界面分组排列。
                    </div>
                </Card>
                {groups.map((group, index) => (
                    <ActionGroup key={`${group.title || "group"}-${index}`} group={group} />
                ))}
            </aside>
            <section className="order-1 min-w-0 rounded-lg border border-border/60 bg-background/50 p-4 lg:order-2">
                <div className="text-base font-semibold">{p.title || "AI 跑步教练"}</div>
                {p.subtitle && <div className="mt-1 text-sm text-muted-foreground">{p.subtitle}</div>}
                {p.status && <div className="mt-3 rounded-lg bg-muted/40 p-3 text-sm leading-6 whitespace-pre-line">{p.status}</div>}
                <div className="mt-3 text-xs text-muted-foreground">
                    可以直接点击左侧卡片开始画像、调整计划或管理知识库。
                </div>
            </section>
        </div>
    )
}
