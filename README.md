# Steemit Auto-Vote

**[English](README.md)** | **[中文](README_CN.md)**

Auto-vote the latest articles from specified Steem authors and claim pending rewards.

## Features

- 🗳️ Auto-vote the latest post from each configured author
- 👤 Auto-vote your own posts
- 🎁 Auto-claim pending rewards (STEEM, SBD, VESTS)
- ⏭️ Skip already-voted and expired (>7 days) posts
- ⏱️ Configurable scan interval for continuous monitoring

## Setup

```bash
git clone https://github.com/omegazhang3/steemit-autovote.git
cd steemit-autovote
npm install
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Description |
|----------|-------------|
| `STEEM_USERNAME` | Your Steem username (without @) |
| `STEEM_POSTING_KEY` | Posting private key (WIF format, starts with 5...) |
| `VOTE_AUTHORS` | Comma-separated authors to vote |
| `VOTE_WEIGHT` | Vote weight: 10000 = 100%, 5000 = 50% |
| `STEEM_API_URL` | API node URL |
| `VOTE_DELAY_MS` | Delay between votes (ms) |
| `SCAN_INTERVAL_MINUTES` | How often to scan (minutes) |

## Hot Reload

Modify `.env` while the bot is running — changes take effect on the next scan cycle. No restart required.

## Usage

```bash
# Run (scans once, then repeats every SCAN_INTERVAL_MINUTES)
node index.js

# Run in background
nohup node index.js >> vote.log 2>&1 &

# Check logs
tail -f vote.log
```

## Security

- Never commit your `.env` file
- Use your **posting** private key only (not active or owner)
- Find it at: steemit.com → Wallet → Permissions → Show Private Key (Posting)
