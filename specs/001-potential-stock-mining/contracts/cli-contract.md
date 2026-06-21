# CLI 接口契约: 潜力标的挖掘

> 定义 `main.py` 新增参数及其行为约定。

---

## 新增参数

```python
# potential stock mining 互斥组
parser.add_argument(
    '--potential-stock-mining',
    action='store_true',
    help='Run potential stock mining (announcement scan + screening)'
)

# 时间范围（与 potential-stock-mining 一起使用）
parser.add_argument(
    '--since',
    type=str,
    default=None,
    help='Scan start date (YYYY-MM-DD). Used with --potential-stock-mining'
)
parser.add_argument(
    '--until',
    type=str,
    default=None,
    help='Scan end date (YYYY-MM-DD). Used with --potential-stock-mining'
)

# 赛道定向（P3）
parser.add_argument(
    '--sector',
    type=str,
    default=None,
    help='Sector filter for industry-targeted mining. Used with --potential-stock-mining'
)
```

## 执行行为

### Mode 4: 潜力标的挖掘模式

当 `--potential-stock-mining` 被指定时，`main()` 进入 Mode 4（而非 Mode 0-3）：

```python
if args.potential_stock_mining:
    # Mode 4: 潜力标的挖掘
    run_potential_stock_mining(config, args)
    return
```

### 参数组合行为

| 组合 | 行为 |
|------|------|
| `--potential-stock-mining` (无时间参数) | 扫描最近一个交易日 |
| `--potential-stock-mining --since 2026-06-01` | 指定起始日期至今 |
| `--potential-stock-mining --since 2026-01-01 --until 2026-06-20` | 指定完整时间范围 |
| `--potential-stock-mining --sector ai_computing_upstream` | 赛道定向筛选 |
| `--potential-stock-mining --stocks 600519` | 单只标的定向扫描 |
| `--potential-stock-mining --dry-run` | 仅获取公告数据，不做 AI 分析 |

### 与 `--stocks` 联用

- `--stocks` 与 `--potential-stock-mining` 同时使用时→仅扫描指定股票的公告
- 不冲突，可在同一命令中同时使用

### 输出格式（控制台）

```
===== 潜力标的挖掘结果 =====
📊 扫描范围: 2026-06-01 ~ 2026-06-20
📋 共扫描 1250 条公告，命中 8 个信号

【P0】并购重组（2条）
  ⭐ 600519 贵州茅台 — 收购XX公司股权（评分 85/100）

【P1】产能扩张（3条）
  ⭐ 600522 中天科技 — 投资建设XX生产基地（评分 72/100）

【P2】业务变更（3条）
  📌 000001 平安银行 — 新增XX业务范围（评分 45/100）

详细报告已保存至数据库。使用 `--report` 参数可导出 Markdown。
```

## 兼容性

- 不修改任何现有参数的含义或行为
- `--potential-stock-mining` 独立于现有模式，不会与 `--market-review` 等参数冲突
- `--dry-run` 在挖掘模式下返回公告获取统计而非分析结果
- `--no-notify` 在挖掘模式下生效（默认不推送，需 `potential_stock_notify_enabled` 配置）
