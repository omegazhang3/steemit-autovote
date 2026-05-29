// 自动给所有 console 输出加时间戳，同时写入日志文件
const fs = require('fs');
require('dotenv').config();
const _origLog = console.log;
const _origErr = console.error;
const _origWarn = console.warn;
const ts = () => {
  const opt = process.env.TIMEZONE ? { timeZone: process.env.TIMEZONE } : {};
  return new Date().toLocaleString('zh-CN', { hour12: false, ...opt });
};
const writeLog = (level, args) => {
  const logFile = process.env.STEEMIT_LOG_FILE || 'steemit_vote.log';
  const line = `[${ts()}] [${level}] ${args.map(a => (typeof a === 'string' ? a : JSON.stringify(a))).join(' ')}\n`;
  try { fs.appendFileSync(logFile, line); } catch (_) {}
};
console.log   = (...a) => { _origLog(`[${ts()}]`, ...a);   writeLog('INFO',  a); };
console.error = (...a) => { _origErr(`[${ts()}]`, ...a);  writeLog('ERROR', a); };
console.warn  = (...a) => { _origWarn(`[${ts()}]`, ...a);  writeLog('WARN',  a); };

const steem = require('steem');
const path = require('path');
const dotenv = require('dotenv');

// 从 .env 读取配置（支持热重载）
function loadConfig() {
  const envPath = path.join(__dirname, '.env');
  const result = dotenv.config({ path: envPath, override: true });
  if (result.error) {
    console.error('❌ Failed to load .env:', result.error.message);
    return null;
  }
  return result.parsed;
}

// 节点管理器
class NodeManager {
  constructor(nodesList) {
    this.nodes = nodesList;
    this.currentIndex = 0;
    this.consecutiveFailures = 0;
    this.maxFailuresPerNode = 3;
  }

  get currentNode() {
    return this.nodes[this.currentIndex];
  }

  reportFailure() {
    this.consecutiveFailures++;
    if (this.consecutiveFailures >= this.maxFailuresPerNode) {
      const oldNode = this.currentNode;
      this.currentIndex = (this.currentIndex + 1) % this.nodes.length;
      this.consecutiveFailures = 0;
      console.warn(`🔄 Node ${oldNode} failed ${this.maxFailuresPerNode}x, switching to ${this.currentNode}`);
      return true;
    }
    return false;
  }

  reportSuccess() {
    this.consecutiveFailures = 0;
  }

  updateNodes(nodesList) {
    if (JSON.stringify(nodesList) !== JSON.stringify(this.nodes)) {
      console.log(`📝 Node list updated: ${nodesList.join(', ')}`);
      this.nodes = nodesList;
      if (this.currentIndex >= this.nodes.length) {
        this.currentIndex = 0;
      }
    }
  }
}

let voter, wif, authors, weight, limit, delay, intervalMinutes;
let nodeMgr;

function applyConfig() {
  const config = loadConfig();
  if (!config) return false;

  const {
    STEEM_USERNAME,
    STEEM_POSTING_KEY,
    VOTE_AUTHORS,
    VOTE_WEIGHT,
    POSTS_LIMIT,
    STEEM_API_URL,
    VOTE_DELAY_MS,
    SCAN_INTERVAL_MINUTES,
  } = process.env;

  if (!STEEM_USERNAME || !STEEM_POSTING_KEY || !VOTE_AUTHORS) {
    console.error('❌ Missing required config. Check .env file.');
    return false;
  }

  // 解析多个节点
  const nodesList = (STEEM_API_URL || 'https://api.steemit.com')
    .split(',')
    .map(n => n.trim())
    .filter(Boolean);

  if (!nodeMgr) {
    nodeMgr = new NodeManager(nodesList);
    console.log(`🚀 Starting with node: ${nodeMgr.currentNode} (${nodeMgr.nodes.length} nodes available)`);
  } else {
    nodeMgr.updateNodes(nodesList);
  }

  steem.api.setOptions({ url: nodeMgr.currentNode });

  voter = STEEM_USERNAME;
  wif = STEEM_POSTING_KEY;
  authors = [voter, ...VOTE_AUTHORS.split(',').map(a => a.trim()).filter(a => a && a !== voter)];
  weight = parseInt(VOTE_WEIGHT, 10) || 10000;
  limit = parseInt(POSTS_LIMIT, 10) || 5;
  delay = parseInt(VOTE_DELAY_MS, 10) || 5000;
  intervalMinutes = parseInt(SCAN_INTERVAL_MINUTES, 10) || 20;

  return true;
}

// 初始加载配置
if (!applyConfig()) {
  process.exit(1);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function getLatestPost(author) {
  try {
    const posts = await steem.api.getDiscussionsByBlogAsync({
      tag: author,
      limit: 10,
    });
    nodeMgr.reportSuccess();
    return posts.find(p => p.author === author) || null;
  } catch (err) {
    console.error(`❌ Failed to fetch posts for @${author}:`, err.message);
    const switched = nodeMgr.reportFailure();
    if (switched) {
      steem.api.setOptions({ url: nodeMgr.currentNode });
      console.log(`🔌 Reconnected to ${nodeMgr.currentNode}`);
    }
    return null;
  }
}

function hasAlreadyVoted(post) {
  return post.active_votes.some(v => v.voter === voter);
}

async function vote(author, permlink) {
  return new Promise((resolve, reject) => {
    steem.broadcast.vote(wif, voter, author, permlink, weight, (err, result) => {
      if (err) reject(err);
      else resolve(result);
    });
  });
}

async function processAuthor(author) {
  console.log(`\n👤 @${author}`);
  const post = await getLatestPost(author);

  if (!post) {
    console.log(`  📭 No posts found`);
    return;
  }

  console.log(`  📝 "${post.title}"`);

  if (hasAlreadyVoted(post)) {
    console.log(`  ⏭️  Already voted, skipping`);
    return;
  }

  const postAge = Date.now() - new Date(post.created + 'Z').getTime();
  const sevenDays = 7 * 24 * 60 * 60 * 1000;
  if (postAge > sevenDays) {
    console.log(`  ⏰ Too old (>7 days), skipping`);
    return;
  }

  try {
    console.log(`  🗳️  Voting (${weight / 100}%)...`);
    await vote(author, post.permlink);
    nodeMgr.reportSuccess();
    console.log(`  ✅ Vote successful!`);
  } catch (err) {
    console.error(`  ❌ Vote failed: ${err.message || JSON.stringify(err)}`);
    const switched = nodeMgr.reportFailure();
    if (switched) {
      steem.api.setOptions({ url: nodeMgr.currentNode });
      console.log(`🔌 Reconnected to ${nodeMgr.currentNode}`);
    }
  }
}

async function claimRewards() {
  try {
    const accounts = await steem.api.getAccountsAsync([voter]);
    if (!accounts || accounts.length === 0) return;

    const account = accounts[0];
    const steemReward = account.reward_steem_balance;
    const sbdReward = account.reward_sbd_balance;
    const vestsReward = account.reward_vesting_balance;

    const hasRewards =
      parseFloat(steemReward) > 0 ||
      parseFloat(sbdReward) > 0 ||
      parseFloat(vestsReward) > 0;

    if (!hasRewards) {
      console.log(`\n🎁 No rewards to claim`);
      return;
    }

    console.log(`\n🎁 Claiming: ${steemReward}, ${sbdReward}, ${vestsReward}...`);
    await new Promise((resolve, reject) => {
      steem.broadcast.claimRewardBalance(wif, voter, steemReward, sbdReward, vestsReward, (err, result) => {
        if (err) reject(err);
        else resolve(result);
      });
    });
    console.log(`  ✅ Rewards claimed!`);
    nodeMgr.reportSuccess();
  } catch (err) {
    console.error(`  ❌ Claim failed: ${err.message || JSON.stringify(err)}`);
    const switched = nodeMgr.reportFailure();
    if (switched) {
      steem.api.setOptions({ url: nodeMgr.currentNode });
      console.log(`🔌 Reconnected to ${nodeMgr.currentNode}`);
    }
  }
}

async function run() {
  // 每次运行前重新加载配置，修改 .env 后无需重启
  applyConfig();

  console.log('🔍 === Scanning ===');
  console.log(`👤 Voter: @${voter}`);
  console.log(`📋 Authors: ${authors.map(a => '@' + a).join(', ')}`);
  console.log(`⚖️  Weight: ${weight / 100}%`);

  for (const author of authors) {
    await processAuthor(author);
  }

  await claimRewards();

  console.log(`\n⏱️  Next scan in ${intervalMinutes} minutes...`);
}

// 使用 setTimeout 递归调用，支持动态调整间隔
async function startLoop() {
  await run();
  const scheduleNext = () => {
    setTimeout(async () => {
      await run();
      scheduleNext();
    }, intervalMinutes * 60 * 1000);
  };
  scheduleNext();
}

startLoop().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
