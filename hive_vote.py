# -*- coding=utf-8 -*-
import os
import time
import json
import logging
import traceback
from dotenv import load_dotenv
from beem import Hive
from beem.price import Price
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo
from beem.market import Market
from beem.account import Account
from beem.comment import Comment
from beem.vote import ActiveVotes
from beembase.operations import Vote
from beem.blockchain import Blockchain
from beem.transactionbuilder import TransactionBuilder

load_dotenv()

# 从 .env 解析 following 列表: "user1:weight1,user2:weight2"
def parse_following(env_str):
    result = []
    for item in env_str.split(","):
        item = item.strip()
        if ":" in item:
            name, weight = item.split(":", 1)
            result.append([name.strip(), int(weight.strip())])
    return result

def load_config():
    """每次调用重新读取 .env，支持动态修改配置"""
    load_dotenv(override=True)
    nodes_str = os.getenv("HIVE_API_URL", "https://api.deathwing.me")
    nodes_list = [n.strip() for n in nodes_str.split(",") if n.strip()]
    return {
        'nodes': nodes_list,
        'account': os.getenv("HIVE_ACCOUNT", ""),
        'posting_key': os.getenv("HIVE_POSTING_KEY", ""),
        'vote_interval': int(os.getenv("HIVE_VOTE_INTERVAL", "15")) * 60,  # 分钟转秒
        'following': parse_following(os.getenv("HIVE_FOLLOWING", "")),
    }

class NodeManager:
    """节点管理器：跟踪当前节点，失败时自动切换"""
    def __init__(self, nodes_list):
        self.nodes = nodes_list
        self.current_index = 0
        self.consecutive_failures = 0
        self.max_failures_per_node = 3

    @property
    def current_node(self):
        return self.nodes[self.current_index]

    def report_failure(self):
        """报告一次失败，达到阈值时切换到下一个节点"""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.max_failures_per_node:
            old_node = self.current_node
            self.current_index = (self.current_index + 1) % len(self.nodes)
            self.consecutive_failures = 0
            logger.warning(f'🔄 Node {old_node} failed {self.max_failures_per_node}x, switching to {self.current_node}')
            return True  # 已切换
        return False  # 未切换

    def report_success(self):
        """成功后重置失败计数"""
        self.consecutive_failures = 0

    def update_nodes(self, nodes_list):
        """动态更新节点列表"""
        if nodes_list != self.nodes:
            logger.info(f'📝 Node list updated: {nodes_list}')
            self.nodes = nodes_list
            if self.current_index >= len(self.nodes):
                self.current_index = 0

class TZFormatter(logging.Formatter):
    """日志格式化器：支持 TIMEZONE 环境变量，未设置则用机器本地时间"""
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt=fmt, datefmt=datefmt)
        tz_name = os.environ.get("TIMEZONE")
        self._tz = ZoneInfo(tz_name) if tz_name else None

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=self._tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

log_format = "%(asctime)s - %(levelname)s - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"
formatter = TZFormatter(fmt=log_format, datefmt=date_format)
file_handler = logging.FileHandler(os.environ.get("HIVE_LOG_FILE", "hive_vote.log"))
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

half_hour = 1800
fifteenMinutes = 900
twentyMinutes = 1200

# 最大连续失败次数，超过后等待更长时间
MAX_CONSECUTIVE_FAILURES = 10
# 连续失败时的退避等待时间（秒）
BACKOFF_BASE = 60

def create_client_and_account(account_name, wif_posting_key, nodes):
    """创建新的 Hive 连接和 Account 对象"""
    client = Hive(keys=[wif_posting_key], node=nodes)
    account = Account(account_name, blockchain_instance=client)
    return client, account

def claimReward(account):
    account.refresh()
    hbd_balance = account['hbd_balance']
    rewardHive = account['reward_hive_balance']
    rewardHbd = account['reward_hbd_balance']
    rewardVests = account['reward_vesting_balance']
    logger.info(f'💰 HBD balance: {hbd_balance}')
    reward = '📋 Reward Balances:' + '\n' + \
          '\t' + str(rewardHive) + '\n' + \
          '\t' + str(rewardHbd) + '\n' + \
          '\t' + str(rewardVests)
    logger.info(reward)
    if rewardHive.amount + rewardHbd.amount + rewardVests.amount == 0:
        logger.info('😴 No rewards to claim')
    else:
        account.claim_reward_balance(reward_hive = float(rewardHive), reward_hbd = float(rewardHbd), reward_vests=rewardVests)
        time.sleep(3)
        logger.info('🎁 All reward balances have been claimed.')
        account.refresh()
        reward_hive = account['reward_hive_balance']
        reward_hbd = account['reward_hbd_balance']
        reward_vests = account['reward_vesting_balance']
        newReward = '📋 After claim reward Balances:' + '\n' + \
              '\t' + str(reward_hive) + '\n' + \
              '\t' + str(reward_hbd) + '\n' + \
              '\t' + str(reward_vests)
        logger.info(newReward)
        time.sleep(1)

def voteFollowers(voter, wif_posting_key, h, following):
    for to_be_vote in following:
        time.sleep(1)
        name = to_be_vote[0]
        weight = to_be_vote[1]
        account_to_be_vote = Account(name, blockchain_instance=h)
        entry = account_to_be_vote.get_blog_entries(0, 1, raw_data=True)[0]
        author = entry["author"]
        permlink = entry["permlink"]
        identifier = ('@' + author + '/' + permlink)
        details = Comment(identifier)
        created = details["created"]
        result = ActiveVotes(identifier, blockchain_instance=h)
        title = f'📊 {len(result)} votes retrieved'
        voted = False
        if result:
            for vote in result :
                if vote['voter'] == voter:
                    voted = True
                    break
        if voted:
            logger.info(f'✅ The post {identifier} (created: {created}) have been voted. {title}')
            continue
        else:
            logger.info(f'📝 The post {identifier} (created: {created}) haven\'t been voted. {title}')
            try:
                tx = TransactionBuilder(blockchain_instance=h)
                tx.appendOps(Vote(**{
                  "voter": voter,
                  "author": author,
                  "permlink": permlink,
                  "weight": int(float(weight) * 100)
                }))
                tx.appendWif(wif_posting_key)
                signed_tx = tx.sign()
                broadcast_tx = tx.broadcast(trx_id=True)
                logger.info(f'👍 {voter} upvote({weight}) {identifier} successfully: {str(broadcast_tx)}')
                time.sleep(1)
            except Exception as e:
                logger.error(f'❌ Vote failed: {str(e)}')
                time.sleep(1)


def main():
    config = load_config()
    account_name = config['account']
    wif_posting_key = config['posting_key']

    if not account_name or not wif_posting_key:
        logger.error("❌ HIVE_ACCOUNT or HIVE_POSTING_KEY not set in .env")
        return

    node_mgr = NodeManager(config['nodes'])
    logger.info(f'🚀 Starting with node: {node_mgr.current_node} ({len(node_mgr.nodes)} nodes available)')

    client, account = create_client_and_account(account_name, wif_posting_key, node_mgr.current_node)

    while True:
        # 每轮重新读取 .env 配置
        config = load_config()
        vote_interval = config['vote_interval']
        following = config['following']
        node_mgr.update_nodes(config['nodes'])

        try:
            logger.info("-----------------------------------------------------------------------------")
            claimReward(account)
            voteFollowers(account_name, wif_posting_key, client, following)
            logger.info(f'💤 Sleep {vote_interval // 60} minutes zzz...')
            time.sleep(vote_interval)
            node_mgr.report_success()  # 成功后重置失败计数
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f'main() exception: {error_detail}')

            # 报告失败，达到阈值自动切换节点
            switched = node_mgr.report_failure()
            if switched:
                # 节点已切换，用新节点重建连接
                try:
                    client, account = create_client_and_account(account_name, wif_posting_key, node_mgr.current_node)
                    logger.info(f'🔌 Reconnected to {node_mgr.current_node}')
                except Exception as re:
                    logger.error(f'❌ Reconnect to {node_mgr.current_node} failed: {traceback.format_exc()}')

            # 指数退避：失败越多等越久，最多 10 分钟
            backoff = min(BACKOFF_BASE * (2 ** (node_mgr.consecutive_failures - 1)), 600)
            logger.info(f'Waiting {backoff}s before retry...')
            time.sleep(backoff)

if __name__ == "__main__":
    main()

