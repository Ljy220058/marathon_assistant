## 📅 周训练计划

| 日期 | 训练类型 | 热身 | 主课（含组数/配速/休息） | 冷身 | 场地 | 备注 |
|------|----------|------|---------------------------|------|------|------|
| 周一 | 节奏跑 | 慢跑12分钟 + 动态拉伸（开合跳、高抬腿、踢腿各30秒） | 30分钟，配速4:40-4:32/km | 慢跑10分钟 + 静态拉伸（股四头肌、臀肌、小腿各30秒×2） | 公路 | 目标: 阈值提升（Z4） |
| 周二 | 休息 | — | — | — | 室内/室外 | 恢复日 |
| 周三 | 有氧阈 | 慢跑12分钟 + 动态拉伸（开合跳、高抬腿、踢腿各30秒） | 40分钟，配速4:57-4:40/km | 慢跑10分钟 + 静态拉伸（股四头肌、臀肌、小腿各30秒×2） | 公路 | 目标: 稳态耐力（Z3） |
| 周四 | 恢复跑 | 慢跑10分钟 + 动态拉伸（高抬腿、后踢腿、弓步各30秒） | 45分钟，配速5:58-5:16/km | 慢跑8分钟 + 静态拉伸（小腿、股四头肌、臀肌各30秒×2） | 公园 | 目标: 恢复能力、基础耐力（Z1） |
| 周五 | 轻松跑 | 慢跑10分钟 + 动态拉伸（高抬腿、后踢腿、弓步各30秒） | 45分钟，配速5:58-5:16/km | 慢跑8分钟 + 静态拉伸（小腿、股四头肌、臀肌各30秒×2） | 公园 | 目标: 恢复能力、基础耐力（Z1） |
| 周六 | 长距离 | 慢跑10分钟 + 动态拉伸（高抬腿、后踢腿、弓步各30秒） | 90分钟，配速5:16-4:57/km | 慢跑8分钟 + 静态拉伸（小腿、股四头肌、臀肌各30秒×2） | 公路 | 目标: 耐力提升（Z2） |
| 周日 | 休息 | — | — | — | 室内/室外 | 恢复日 |

> 💡 执行提醒：根据当日体感微调配速 ±5秒，如出现关节疼痛立即停止并咨询教练。每周至少安排 1 天完全休息。

### 📚 决策草案对象 (Decision Draft Objects)
<details>
<summary>点击查看结构化决策元数据（含 draft.status / adjustments / warnings）</summary>

```json
[
  {
    "day": "周一",
    "type": "节奏跑",
    "draft": {
      "status": "ready",
      "adjustments": [
        "duration_min 按 mid 档位取值为 30"
      ],
      "warnings": [],
      "constraints": [
        {
          "constraint_id": "c_quality_sessions_weekly_cap",
          "label": "每周质量课最多 2 次",
          "rule": "quality_sessions_per_week <= 2",
          "status": "ok",
          "message": "约束满足或当前上下文不足以触发。"
        },
        {
          "constraint_id": "c_quality_gap_48h",
          "label": "高质量课间隔至少 48 小时",
          "rule": "hours_between_quality_sessions >= 48",
          "status": "ok",
          "message": "约束满足或当前上下文不足以触发。"
        }
      ],
      "template_id": "tpl_tempo_continuous_v1",
      "zone_label": "Z4",
      "parameters": {
        "duration_min": "30",
        "intensity": "Z4",
        "rest": "无",
        "surface": "公路"
      },
      "context": {
        "week_history": [],
        "last_quality_day": "",
        "quality_count": 0,
        "quality_sessions_this_week": 0,
        "long_runs_this_week": 0,
        "last_quality_hours_ago": null,
        "previous_day_was_quality": false
      },
      "rendered": "| 周一 | 节奏跑 | 慢跑12分钟 + 动态拉伸（开合跳、高抬腿、踢腿各30秒） | 30分钟，配速4:40-4:32/km | 慢跑10分钟 + 静态拉伸（股四头肌、臀肌、小腿各30秒×2） | 公路 | 目标: 阈值提升（Z4） |"
    },
    "decision_trace": [
      {
        "requested": "节奏跑",
        "status": "ready"
      }
    ]
  },
  {
    "day": "周二",
    "type": "休息",
    "draft": {
      "status": "ready",
      "adjustments": [],
      "warnings": [],
      "constraints": [],
      "parameters": {},
      "context": {
        "week_history": [
          {
            "day": "周一",
            "type": "节奏跑"
          }
        ],
        "last_quality_day": "周一",
        "quality_count": 1,
        "quality_sessions_this_week": 1,
        "long_runs_this_week": 0,
        "last_quality_hours_ago": 24,
        "previous_day_was_quality": true
      },
      "rendered": "| 周二 | 休息 | — | — | — | 室内/室外 | 恢复日 |"
    },
    "decision_trace": [
      {
        "requested": "休息",
        "status": "ready"
      }
    ]
  },
  {
    "day": "周三",
    "type": "有氧阈",
    "draft": {
      "status": "ready",
      "adjustments": [
        "duration_min 按 mid 档位取值为 40"
      ],
      "warnings": [],
      "constraints": [
        {
          "constraint_id": "c_quality_gap_48h",
          "label": "高质量课间隔至少 48 小时",
          "rule": "hours_between_quality_sessions >= 48",
          "status": "ok",
          "message": "约束满足或当前上下文不足以触发。"
        }
      ],
      "template_id": "tpl_aerobic_threshold_continuous_v1",
      "zone_label": "Z3",
      "parameters": {
        "duration_min": "40",
        "intensity": "Z3",
        "rest": "无",
        "surface": "公路"
      },
      "context": {
        "week_history": [
          {
            "day": "周一",
            "type": "节奏跑"
          },
          {
            "day": "周二",
            "type": "休息"
          }
        ],
        "last_quality_day": "周一",
        "quality_count": 1,
        "quality_sessions_this_week": 1,
        "long_runs_this_week": 0,
        "last_quality_hours_ago": 48,
        "previous_day_was_quality": false
      },
      "rendered": "| 周三 | 有氧阈 | 慢跑12分钟 + 动态拉伸（开合跳、高抬腿、踢腿各30秒） | 40分钟，配速4:57-4:40/km | 慢跑10分钟 + 静态拉伸（股四头肌、臀肌、小腿各30秒×2） | 公路 | 目标: 稳态耐力（Z3） |"
    },
    "decision_trace": [
      {
        "requested": "有氧阈",
        "status": "ready"
      }
    ]
  },
  {
    "day": "周四",
    "type": "恢复跑",
    "draft": {
      "status": "ready",
      "adjustments": [
        "duration_min 按 mid 档位取值为 45"
      ],
      "warnings": [],
      "constraints": [
        {
          "constraint_id": "c_easy_after_quality",
          "label": "高质量课后优先恢复或轻松跑",
          "rule": "day_after_quality in {'easy_run','recovery','rest'}",
          "status": "ok",
          "message": "约束满足或当前上下文不足以触发。"
        }
      ],
      "template_id": "tpl_easy_run_duration_v1",
      "zone_label": "Z1",
      "parameters": {
        "duration_min": "45",
        "intensity": "Z1",
        "rest": "无",
        "surface": "公园"
      },
      "context": {
        "week_history": [
          {
            "day": "周一",
            "type": "节奏跑"
          },
          {
            "day": "周二",
            "type": "休息"
          },
          {
            "day": "周三",
            "type": "有氧阈"
          }
        ],
        "last_quality_day": "周一",
        "quality_count": 1,
        "quality_sessions_this_week": 1,
        "long_runs_this_week": 0,
        "last_quality_hours_ago": 72,
        "previous_day_was_quality": false
      },
      "rendered": "| 周四 | 恢复跑 | 慢跑10分钟 + 动态拉伸（高抬腿、后踢腿、弓步各30秒） | 45分钟，配速5:58-5:16/km | 慢跑8分钟 + 静态拉伸（小腿、股四头肌、臀肌各30秒×2） | 公园 | 目标: 恢复能力、基础耐力（Z1） |"
    },
    "decision_trace": [
      {
        "requested": "恢复跑",
        "status": "ready"
      }
    ]
  },
  {
    "day": "周五",
    "type": "轻松跑",
    "draft": {
      "status": "ready",
      "adjustments": [
        "duration_min 按 mid 档位取值为 45"
      ],
      "warnings": [],
      "constraints": [
        {
          "constraint_id": "c_easy_after_quality",
          "label": "高质量课后优先恢复或轻松跑",
          "rule": "day_after_quality in {'easy_run','recovery','rest'}",
          "status": "ok",
          "message": "约束满足或当前上下文不足以触发。"
        }
      ],
      "template_id": "tpl_easy_run_duration_v1",
      "zone_label": "Z1",
      "parameters": {
        "duration_min": "45",
        "intensity": "Z1",
        "rest": "无",
        "surface": "公园"
      },
      "context": {
        "week_history": [
          {
            "day": "周一",
            "type": "节奏跑"
          },
          {
            "day": "周二",
            "type": "休息"
          },
          {
            "day": "周三",
            "type": "有氧阈"
          },
          {
            "day": "周四",
            "type": "恢复跑"
          }
        ],
        "last_quality_day": "周一",
        "quality_count": 1,
        "quality_sessions_this_week": 1,
        "long_runs_this_week": 0,
        "last_quality_hours_ago": 96,
        "previous_day_was_quality": false
      },
      "rendered": "| 周五 | 轻松跑 | 慢跑10分钟 + 动态拉伸（高抬腿、后踢腿、弓步各30秒） | 45分钟，配速5:58-5:16/km | 慢跑8分钟 + 静态拉伸（小腿、股四头肌、臀肌各30秒×2） | 公园 | 目标: 恢复能力、基础耐力（Z1） |"
    },
    "decision_trace": [
      {
        "requested": "轻松跑",
        "status": "ready"
      }
    ]
  },
  {
    "day": "周六",
    "type": "长距离",
    "draft": {
      "status": "ready",
      "adjustments": [
        "duration_min 按 mid 档位取值为 100",
        "duration_min 受单次时长上限约束，下调到 90"
      ],
      "warnings": [],
      "constraints": [
        {
          "constraint_id": "c_long_run_weekly_cap",
          "label": "每周长距离最多 1 次",
          "rule": "long_run_sessions_per_week <= 1",
          "status": "ok",
          "message": "约束满足或当前上下文不足以触发。"
        },
        {
          "constraint_id": "c_long_run_duration_cap",
          "label": "长距离时长不得超过单次上限",
          "rule": "long_run_duration_min <= athlete.max_session_minutes",
          "status": "ok",
          "message": "约束满足或当前上下文不足以触发。"
        }
      ],
      "template_id": "tpl_long_run_base_v1",
      "zone_label": "Z2",
      "parameters": {
        "duration_min": "90",
        "intensity": "Z2",
        "progression": "optional_last_20min",
        "surface": "公路"
      },
      "context": {
        "week_history": [
          {
            "day": "周一",
            "type": "节奏跑"
          },
          {
            "day": "周二",
            "type": "休息"
          },
          {
            "day": "周三",
            "type": "有氧阈"
          },
          {
            "day": "周四",
            "type": "恢复跑"
          },
          {
            "day": "周五",
            "type": "轻松跑"
          }
        ],
        "last_quality_day": "周一",
        "quality_count": 1,
        "quality_sessions_this_week": 1,
        "long_runs_this_week": 0,
        "last_quality_hours_ago": 120,
        "previous_day_was_quality": false
      },
      "rendered": "| 周六 | 长距离 | 慢跑10分钟 + 动态拉伸（高抬腿、后踢腿、弓步各30秒） | 90分钟，配速5:16-4:57/km | 慢跑8分钟 + 静态拉伸（小腿、股四头肌、臀肌各30秒×2） | 公路 | 目标: 耐力提升（Z2） |"
    },
    "decision_trace": [
      {
        "requested": "长距离",
        "status": "ready"
      }
    ]
  },
  {
    "day": "周日",
    "type": "休息",
    "draft": {
      "status": "ready",
      "adjustments": [],
      "warnings": [],
      "constraints": [],
      "parameters": {},
      "context": {
        "week_history": [
          {
            "day": "周一",
            "type": "节奏跑"
          },
          {
            "day": "周二",
            "type": "休息"
          },
          {
            "day": "周三",
            "type": "有氧阈"
          },
          {
            "day": "周四",
            "type": "恢复跑"
          },
          {
            "day": "周五",
            "type": "轻松跑"
          },
          {
            "day": "周六",
            "type": "长距离"
          }
        ],
        "last_quality_day": "周一",
        "quality_count": 1,
        "quality_sessions_this_week": 1,
        "long_runs_this_week": 1,
        "last_quality_hours_ago": 144,
        "previous_day_was_quality": false
      },
      "rendered": "| 周日 | 休息 | — | — | — | 室内/室外 | 恢复日 |"
    },
    "decision_trace": [
      {
        "requested": "休息",
        "status": "ready"
      }
    ]
  }
]
```

</details>


===USAGE===
{'prompt_tokens': 555, 'completion_tokens': 48, 'total_tokens': 603}