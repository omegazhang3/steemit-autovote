# Steemit 自动点赞

**[English](README.md)** | **[中文](README_CN.md)**

自动为指定 Steem 作者的最新文章点赞，并自动领取待领奖励。

## 功能

- 🗳️ 自动为每位配置作者的最新文章点赞
- 👤 自动为自己的文章点赞
- 🎁 自动领取待领奖励（STEEM、SBD、VESTS）
- ⏭️ 跳过已点赞和过期（>7天）的文章
- ⏱️ 可配置扫描间隔，持续监控

## 安装

```bash
git clone https://github.com/omegazhang3/steemit-autovote.git
cd steemit-autovote
npm install
cp .env.example .env
```

编辑 `.env` 填入你的配置：

| 变量 | 说明 |
|------|------|
| `STEEM_USERNAME` | Steem 用户名（不带 @） |
| `STEEM_POSTING_KEY` | Posting 私钥（WIF 格式，以 5 开头） |
| `VOTE_AUTHORS` | 要点赞的作者，逗号分隔 |
| `VOTE_WEIGHT` | 点赞权重：10000 = 100%，5000 = 50% |
| `STEEM_API_URL` | API 节点地址 |
| `VOTE_DELAY_MS` | 点赞间隔（毫秒） |
| `SCAN_INTERVAL_MINUTES` | 扫描间隔（分钟） |

## 热重载

运行期间修改 `.env` 文件，下次扫描自动生效，无需重启。

## 使用

```bash
# 运行（立即扫描一次，之后每隔设定时间重复）
node index.js

# 后台运行
nohup node index.js >> vote.log 2>&1 &

# 查看日志
tail -f vote.log
```

## 安全提醒

- 不要提交 `.env` 文件
- 只使用 **Posting** 私钥（不要用 Active 或 Owner）
- 获取方式：steemit.com → 钱包 → 权限 → 显示私钥（Posting）
