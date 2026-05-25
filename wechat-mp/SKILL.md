---
name: wechat-mp
description: Use when user wants to create, edit, or publish content to WeChat Official Account (微信公众号). Covers topic selection from WeChat Reading notes, article editing with storytelling tone, styled HTML conversion, and full API-based draft publishing. Trigger words: 公众号、发文、选题、编辑发布、微信发布.
---

# 微信公众号全流程助手

## 概览

三段式 SOP：**选题 → 编辑 → 发布**

前置要求：环境变量 `WECHAT_MP_APPID` + `WECHAT_MP_SECRET` 已配置（存入 `~/.claude/settings.json` 的 env 节点）。

---

## 阶段一：选题

### 来源优先级
1. **用户已有书籍/笔记**：调用 `weread-skills` 拉取用户微信读书笔记，按主题聚类提炼选题
2. **用户直接给定**：接收题目或方向，跳到编辑阶段
3. **无输入时**：根据用户书架最近阅读领域推荐 3 个方向供选择

### 选题标准
- 有一个「读者痛点」或「反直觉结论」作为钩子
- 核心内容能用「5 个方法」「3 个原则」等结构承载
- 500 字内能讲清楚核心

### 微信推荐机制适配（必读）

微信内容分发依赖**完读率、分享率、收藏率**三项指标，选题时优先选以下高传播模式：

**① 关系场景锚定**（最高传播系数）
- 在标题或开篇植入真实关系角色，让读者「对号入座」后自发转发
- 优先关系词：男朋友 / 女朋友 / 老公 / 老婆 / 闺蜜 / 死党 / 父母 / 前任
- 示例套路：
  - `「你男朋友懂不懂这件事，决定了你们能不能走到最后」`
  - `「和闺蜜吵架之后，我才明白真正的友情是什么样的」`
  - `「我老公做了这件事，让我突然觉得这段婚姻值了」`

**② 冲突/反转结构**（完读率最高）
- 文章必须有一个明显的冲突节点，读者要「想看结果」才会读完
- 冲突类型：
  - **期待落差型**：「我以为他爱我，直到那天晚上…」
  - **价值观对撞型**：「大多数人觉得这很正常，但我认为这恰恰是问题所在」
  - **身份反转型**：「那个让我最烦的人，后来救了我」
- 冲突在**第二段**引出，不要超过 300 字才出现

**③ 高传播标题公式**
```
[关系词] + [反常识/强情绪动词] + [具体结论/数字]
例：「你老公每天说的这3句话，正在悄悄伤害你」
例：「闺蜜突然消失，我花了一年才想清楚为什么」
例：「男朋友不愿意做这件事，你就别嫁给他」
```

**④ 情绪共鸣词库**（嵌入正文）
- 委屈 / 心疼 / 忍了很久 / 突然就懂了 / 第一次觉得 / 一瞬间 / 哭了
- 这类词出现时，读者的分享冲动显著上升

---

## 阶段二：编辑

### 语气规范（公众号友好）
- **开篇**：从读者熟悉的场景/困境切入，先共情再给解法；**尽量绑定一个具体关系角色**（男朋友/闺蜜/父母），让读者代入
- **每节**：先讲「你肯定遇到过的情况」，再给具体操作
- **冲突节点**（必须有）：第二段或第一节末尾埋一个「但是…」转折，制造张力，让读者必须继续读
- **结尾**：给一个可执行的行动指令 + 一句有记忆点的金句；收尾句如能引发「我要转给某人看」的冲动最佳

### 结构模板
```
开篇：关系角色 + 场景共鸣（100字内）
↓
冲突节点：期待落差 / 价值观对撞 / 身份反转（50-100字）
↓
方法01/原则01：场景 → 解法 → 图片
方法02... （最多5节）
↓
收尾：行动清单 + 情绪共鸣金句（隐含「转给他/她看」的暗示）
```

### 写作检查清单（发布前必过）
- [ ] 标题含关系词或强情绪词
- [ ] 开篇 200 字内出现冲突或反转
- [ ] 至少一处「你肯定也…」或「如果你也遇到过…」的读者代入句
- [ ] 结尾有一句值得截图的金句
- [ ] 全文没有干货堆砌感，每个方法都有具体的「人」和「事」

### 保存文件
写完后保存为本地 Markdown：`~/doc/notes/[文章标题].md`
图片引用使用本地路径，发布时自动上传替换。

---

## 阶段三：发布

### 环境检查
```bash
echo $WECHAT_MP_APPID   # 应输出 wx...
echo $WECHAT_MP_SECRET  # 应输出密钥
```

若未配置，引导用户：
```bash
# 写入 ~/.claude/settings.json 的 env 节点
WECHAT_MP_APPID=wxXXXXXXXX
WECHAT_MP_SECRET=XXXXXXXX
```

### IP 白名单（首次必做）

微信 API 要求调用方 IP 在白名单内。首次使用时：

```bash
# 查本机出口 IP
curl -s -x "http://127.0.0.1:18765" https://api.ipify.org
```

将输出的 IP 添加到：公众号后台 → 设置与开发 → 基本配置 → IP白名单

**注意**：IP 可能有多个出口节点，如报 40164 错误需重新查 IP 并补充白名单。

### 发布流程（用 `scripts/publish.py`）

```bash
python3 ~/.claude/skills/wechat-mp/scripts/publish.py \
  --md ~/doc/notes/文章标题.md \
  --cover ~/doc/img/封面图.png
```

脚本自动完成：
1. 获取 access_token（含重试，应对多出口 IP 问题）
2. 上传文章内图片（`uploadimg` 接口，返回 CDN URL）
3. 上传封面图为永久素材（`add_material` 接口，返回 media_id）
4. 将 Markdown 转为微信兼容的内联样式 HTML
5. 调用 `draft/add` 创建草稿
6. 输出草稿 ID，提示用户去后台发布

### 最后一步（后台操作）

自动发布 (`freepublish`) 需已认证服务号权限。订阅号需手动：

> mp.weixin.qq.com → 内容 → 草稿箱 → 找到文章 → 发布

---

## HTML 样式规范

微信只支持**内联样式**，核心样式变量：

```python
P      = 'margin:0 0 1.4em 0; font-size:17px; line-height:1.9; color:#333; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;'
H2_NUM = 'display:inline-block; background:#1a1a1a; color:#fff; font-size:12px; font-weight:700; letter-spacing:0.12em; padding:3px 10px; border-radius:2px; margin-right:8px;'
H2_TXT = 'font-size:22px; font-weight:700; color:#1a1a1a; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;'
IMG    = 'width:100%; border-radius:6px; margin:1.4em 0; display:block;'
QUOTE  = 'border-left:3px solid #1a1a1a; margin:1.6em 0; padding:0.8em 1.2em; background:#f7f7f7; border-radius:0 4px 4px 0;'
CLOSE  = 'background:#1a1a1a; color:#fff; padding:2em 1.6em; border-radius:8px; margin:2em 0;'
```

---

## 常见错误

| 错误码 | 含义 | 解决 |
|--------|------|------|
| 40164 | IP 未在白名单 | 查出口 IP 并添加到公众号后台白名单 |
| 40001 | access_token 无效 | 重新获取 token（有效期 2 小时） |
| 48001 | API 权限不足 | freepublish 需服务号，订阅号手动发布 |
| 40007 | media_id 无效 | 封面图重新上传 |
| 45009 | 接口调用超限 | access_token 每天限 2000 次 |
