# Steemit & Hive Auto-Vote

**[English](README.md)** | **[中文](README_CN.md)**

Auto-vote the latest articles from specified Steem/Hive authors and claim pending rewards.

## Features

- 🗳️ Auto-vote the latest post from each configured author
- 👤 Auto-vote your own posts
- 🎁 Auto-claim pending rewards (STEEM, SBD, VESTS)
- ⏭️ Skip already-voted and expired (>7 days) posts
- ⏱️ Configurable scan interval for continuous monitoring
- 🐝 **Hive support** — auto-vote Hive bloggers with node failover
- 🔄 Hot reload — modify `.env` while running, no restart needed

## Setup

```bash
git clone https://github.com/omegazhang3/steemit-autovote.git
cd steemit-autovote
npm install
cp .env.example .env
```

Edit `.env` with your credentials:

### Steem

| Variable | Description |
|----------|-------------|
| `STEEM_USERNAME` | Your Steem username (without @) |
| `STEEM_POSTING_KEY` | Posting private key (WIF format, starts with 5...) |
| `VOTE_AUTHORS` | Comma-separated authors to vote |
| `VOTE_WEIGHT` | Vote weight: 10000 = 100%, 5000 = 50% |
| `STEEM_API_URL` | API node URL |
| `VOTE_DELAY_MS` | Delay between votes (ms) |
| `SCAN_INTERVAL_MINUTES` | How often to scan (minutes) |

### Hive

| Variable | Description |
|----------|-------------|
| `HIVE_ACCOUNT` | Your Hive username (without @) |
| `HIVE_POSTING_KEY` | Hive posting private key (WIF format) |
| `HIVE_API_URL` | Comma-separated API nodes for failover |
| `HIVE_FOLLOWING` | Authors to vote: `user1:weight1,user2:weight2` |
| `HIVE_VOTE_INTERVAL` | Vote interval in minutes |

## Usage

### Steem

```bash
node steemit_vote.js

# Background
nohup node steemit_vote.js >> steemit_vote.log 2>&1 &

# Logs
tail -f steemit_vote.log
```

### Hive

```bash
# Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install beem python-dotenv

# Run
python3 hive_vote.py

# Background
nohup venv/bin/python3 hive_vote.py &

# Logs
tail -f hive_steemit_vote.log
```

## Security

- Never commit your `.env` file
- Use your **posting** private key only (not active or owner)
- Find it at: steemit.com → Wallet → Permissions → Show Private Key (Posting)
