---
name: tencentwm-export-trans
description: >-
  Export Tencent Wealth Management (腾讯理财通) transaction bills to CSV via
  export_trans_bills.py. Use when the user asks for 理财通交易记录、账单导出、
  tencentwm bills, or to fetch/sync their 理财通成交/申购赎回流水.
---

# 腾讯理财通交易记录导出

从理财通官网 API 拉取交易账单，导出为 CSV。使用本 skill 自带脚本，**不要**重写抓取逻辑。

## 脚本路径

```
~/.cursor/skills/tencentwm-export-trans/scripts/export_trans_bills.py
```

绝对路径：

```
/Users/haojunsheng/.cursor/skills/tencentwm-export-trans/scripts/export_trans_bills.py
```

## 何时使用

- 用户要「理财通交易记录」「账单」「流水」「导出 CSV」
- 用户要按日期范围拉取、更新本地交易数据
- 用户要把理财通数据交给后续分析（记账、对账、统计）

**不适用**：非理财通渠道（微信支付账单、银行卡流水）→ 不要用本脚本。

## 前置条件

1. **Cookie 必须有效**（登录 `https://www.tencentwm.com` 后的请求 Cookie）
2. **网络可达** `www.tencentwm.com`
3. Python 3，仅用标准库（无需 pip 安装）

### Cookie 获取（用户需浏览器操作）

1. 浏览器登录 [理财通交易明细](https://www.tencentwm.com/web/v3/account/trans_detail.shtml)
2. 打开开发者工具 → Network，刷新或翻页，找到 `QueryTransBillList` 请求
3. 复制请求头里的完整 `Cookie` 值

**安全**：Cookie 等同登录凭证。禁止写入 git、禁止在回复里完整粘贴。优先用本地文件或环境变量。

推荐本地存放（勿提交版本库）：

```bash
# 示例：单行 cookie 文件
~/.config/tencentwm/cookie.txt
```

## 执行命令

工作目录任意；脚本用绝对路径最稳妥。

### 默认：全量至今

```bash
python3 ~/.cursor/skills/tencentwm-export-trans/scripts/export_trans_bills.py \
  --cookie-file ~/.config/tencentwm/cookie.txt \
  -o ~/Downloads/tencentwm_trans_bills.csv \
  -v
```

### 指定日期范围

日期格式 `YYYYMMDD`：

```bash
python3 ~/.cursor/skills/tencentwm-export-trans/scripts/export_trans_bills.py \
  --cookie-file ~/.config/tencentwm/cookie.txt \
  --start-date 20250101 \
  --end-date 20260515 \
  -o ~/Downloads/tencentwm_2025.csv \
  -v
```

### Cookie 传入方式（三选一）

| 方式 | 用法 |
|------|------|
| 文件 | `--cookie-file ~/.config/tencentwm/cookie.txt` |
| 环境变量 | `export TENCENTWM_COOKIE='...'` 后省略 `-c` |
| 参数 | `-c '...'`（避免在命令历史里留痕） |

## 参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `--start-date` | `20140101` | 查询起始日 |
| `--end-date` | 今天 | 查询结束日 |
| `-o` / `--output` | 带时间戳的 csv | 输出路径 |
| `--page-info` | `{"accTime":""}` | 分页游标，首屏一般不用改 |
| `--max-pages` | `500` | 分页上限（防死循环） |
| `-v` | 关 | 打印分页进度到 stderr |

成功时 stdout：`Exported N rows -> <绝对路径>`。

## 输出 CSV 字段

| 列名 | 含义 |
|------|------|
| `acc_time` | 记账时间 |
| `bill_name` | 账单名称 |
| `bill_fee_yuan` | 金额（元，已由分换算） |
| `bill_sub_desc` | 副标题/说明 |
| `bill_busi_type` | 业务类型 |
| `bill_state` / `bill_show_state` | 状态 |
| `fund_code` / `spid` / `fund_brief_name` | 基金信息 |
| `fund_date` | 基金日期 |
| `bill_listid` | 账单 ID |
| `asset_change_type` | 资产变动类型 |
| `plain_unit` / `bill_unit` / `bill_unit_text` | 份额/单位 |

导出后可用 `head`、`wc -l` 或 pandas 做校验；向用户汇报行数、日期范围、输出路径。

## 标准工作流

```
任务进度：
- [ ] 确认日期范围与输出路径
- [ ] 确认 Cookie 可用（文件存在或用户已设置 TENCENTWM_COOKIE）
- [ ] 运行 export_trans_bills.py（加 -v）
- [ ] 检查 Exported N rows 与 CSV 行数
- [ ] 向用户汇报结果（不泄露 Cookie）
```

用户未给日期时：先问「要全量还是某段时间？」；未给输出路径时：默认 `~/Downloads/tencentwm_trans_<start>_<end>.csv`。

## 故障排查

| 现象 | 处理 |
|------|------|
| `Cookie is required` | 配置 `--cookie-file` / `TENCENTWM_COOKIE` / `-c` |
| `HTTP 401/403` 或 `retcode≠0` | Cookie 过期 → 请用户在浏览器重新登录并更新 cookie 文件 |
| `Network error` | 检查网络/VPN；确认能访问 tencentwm.com |
| 行数为 0 | 扩大日期范围；确认该时段确有交易 |
| 行数少于预期 | 加 `-v` 看分页是否提前结束；必要时增大 `--max-pages` |

`retcode` 非 `0` 时脚本会打印 `retmsg`，原样转告用户即可。

## 用户后续分析

用户若要统计、对账、可视化：

1. 先确保 CSV 导出成功
2. 再按用户需求用 pandas / Excel / 自定义脚本处理
3. 金额列用 `bill_fee_yuan`；时间列用 `acc_time`

## 禁止事项

- 不要把 Cookie 提交到 git 或写在 SKILL/代码里
- 不要为实现导出而另写一套 API 调用（维护脚本即可）
- 不要在未确认的情况下把 CSV 上传到公共位置
