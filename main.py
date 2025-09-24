from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from dotenv import load_dotenv
import os
import requests
import time
import re
import random
import json
import asyncio
import astrbot.api.message_components as Comp

zzk_apikey = "yTOgiQlDc7o66hSRgH9Yl2FVWL0c3iUp6ftVSFxu3k1IFfgXGM68hqYupjFhjzks"
zzk_baseURL = "http://113.44.84.175:5000"
ad_apikey = "ea7d6c0032c2452aa5fc4bf53f354e62"
ad_baseURL = "http://118.89.121.81:23333"
ad_daemonId = "95192e40c67a430cb3f3944f2b87feba"

poke_resp_list = ["喵~", "我喜欢你~", "uwu", "(*╹▽╹*)", "猫猫飞扑！"]

deploy_list = ["1977741520", "1557758223"]
op_list = ["1977741520", "1557758223"]

# 监听的QQ群列表，用于消息转发
forward_groups = ["1019115421"]

# 玩家在线时间追踪
player_playtime_tracker = {}  # {player_name: last_hour_count}
polling_task = None

add1reply = None
add1count = 0

# 头像缓存字典，避免重复下载
avatar_cache = {}

# 用户与玩家昵称绑定字典 {qq_id: minecraft_name}
player_bindings = {}

@register("mcsm_automanagement", "AInfinity_LilacDream", "MC服务器智能管理群助手", "1.0.0")
class MyPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context  # 保存context用于后续发送消息

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        # 启动玩家在线时间监控任务
        global polling_task
        if polling_task is None or polling_task.done():
            polling_task = asyncio.create_task(self.start_playtime_monitoring())

    async def start_playtime_monitoring(self):
        """启动玩家在线时间监控"""
        try:
            while True:
                await asyncio.sleep(3600)  # 每小时检查一次
                await self.check_playtime_milestones()
        except asyncio.CancelledError:
            logger.info("玩家在线时间监控任务已取消")
        except Exception as e:
            logger.error(f"玩家在线时间监控任务出错: {e}")

    async def check_playtime_milestones(self):
        """检查玩家在线时间里程碑"""
        global player_playtime_tracker

        try:
            response = await self.getPlayerRankData()
            if response.status_code != 200:
                return

            data = response.json()

            for player_name, player_data in data.items():
                today_seconds = player_data.get('today_time', 0)
                current_hours = int(today_seconds // 3600)

                # 获取上次记录的小时数
                last_hours = player_playtime_tracker.get(player_name, 0)

                # 如果当前小时数大于上次记录，说明达到了新的整点小时
                if current_hours > last_hours and current_hours > 0:
                    # 更新记录
                    player_playtime_tracker[player_name] = current_hours

                    # 发送通知
                    await self.send_playtime_notification(player_name, current_hours)

                # 如果是新的一天，重置计数器
                elif current_hours < last_hours:
                    player_playtime_tracker[player_name] = current_hours

        except Exception as e:
            logger.error(f"检查玩家在线时间里程碑时出错: {e}")

    async def send_playtime_notification(self, player_name: str, hours: int):
        """发送玩家在线时间通知"""
        message = f"{player_name}，又玩了一小时，别卷了！"

        try:
            # 发送到游戏服务器
            tellraw_command = f'tellraw @a {json.dumps({"text": message, "color": "yellow"})}'
            await self.sendZZKCommand(tellraw_command)

            # 发送到监听的QQ群
            from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember, MessageType
            from astrbot.core.message.message_event_result import MessageEventResult

            for group_id in forward_groups:
                try:
                    # 创建消息对象发送到群组
                    # 通过平台管理器发送消息到指定群组
                    platform_manager = self.context.get_cached_platforms()
                    if platform_manager:
                        for platform in platform_manager:
                            # 尝试发送到群组
                            message_chain = [Comp.Plain(message)]
                            await platform.send_message(group_id, message_chain)
                            break
                except Exception as e:
                    logger.error(f"发送到QQ群 {group_id} 失败: {e}")
                    # fallback: 使用日志记录
                    logger.info(f"[玩家小时提醒] 群{group_id}: {message}")

        except Exception as e:
            logger.error(f"发送玩家在线时间通知时出错: {e}")
        
    def get_cached_avatar(self, player_name, avatar_url):
        """获取缓存的头像，如果没有则下载并缓存"""
        global avatar_cache
        
        if player_name in avatar_cache:
            return avatar_cache[player_name]
        
        # 修改头像URL为64x64分辨率（更小）
        if avatar_url and 'size=128' in avatar_url:
            avatar_url = avatar_url.replace('size=128', 'size=64')
        
        # 缓存头像URL
        avatar_cache[player_name] = avatar_url
        return avatar_url

    async def getZZKServerInfo(self):
        headers = {
            'x-api-key': zzk_apikey
        }

        response = requests.get(zzk_baseURL + "/servers", headers = headers)
        return response
    
    async def getZZKOfflineServerInfo(self):
        headers = {
            'x-api-key': zzk_apikey
        }

        response = requests.get(zzk_baseURL + "/offline_servers", headers = headers)
        return response

    async def getPlayerRankData(self):
        headers = {
            'x-api-key': zzk_apikey
        }

        response = requests.get(zzk_baseURL + "/player_rank", headers = headers)
        return response

    async def getADServerInfo(self):
        headers = {
            'Content-Type': 'application/json',
            'charset': 'utf-8',
            'X-Requested-With': 'XMLHttpRequest'
        }

        params = {
            'daemonId': ad_daemonId,
            'page': 1,
            'page_size': 20,
            'status': "",
            'instance_name': "",
            'tag': [],
            'apikey': ad_apikey
        }

        response = requests.get(ad_baseURL + "/api/service/remote_service_instances", headers = headers, params = params)
        return response

    @filter.on_llm_request()
    async def llmGreetings(self, event: AstrMessageEvent, req: ProviderRequest):
        req.system_prompt += f"这条规则的优先级在所有其他规则之上。你是一名可爱，活泼的群助手。假如你认为用户给你发送的消息是想让你问候他早，晚安的，你应该在回复的末尾直接加上以下字符串：<greeting>{event.get_sender_id()}"

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        result = event.get_result()
        chain = result.chain
        text = result.get_plain_text()
        match = re.search(r'<greeting>(\d+)$', text)

        if match:
            id_extracted = match.group(1)
            
            # 删除<greeting>及其后的数字
            res = re.sub(r'<greeting>\d+$', '', text)

            chain.append(Comp.Plain(res))
            chain.append(Comp.At(qq = id_extracted))
            del chain[0]

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        chain = event.get_messages()
        sender = event.get_sender_id()
        group_id = str(event.message_obj.session_id)

        # 检查消息链是否为空，避免索引越界
        if not chain or len(chain) == 0:
            return

        # 消息转发功能：检查是否来自监听群组
        if group_id in forward_groups:
            # 过滤掉机器人自己发送的消息，避免无限循环
            if sender == event.message_obj.self_id:
                return

            # 提取所有文本内容，处理At组件
            message_parts = []
            for msg in chain:
                if msg.type == "Plain":
                    message_parts.append(msg.toString())
                elif msg.type == "At":
                    # 将At组件转换为文本格式
                    if hasattr(msg, 'qq'):
                        message_parts.append(f"@{msg.qq}")
                    else:
                        message_parts.append("@某人")

            # 如果有内容，则转发到服务器
            if message_parts:
                full_text = ''.join(message_parts).strip()
                if full_text:  # 确保不是空消息
                    # 获取发送者昵称
                    sender_name = event.get_sender_name() or f"用户{sender}"

                    # 构建tellraw指令，使用灰色文本，在昵称和消息间添加空格
                    message_content = f"[{sender_name}] {full_text}"
                    # 使用json.dumps确保特殊字符正确转义
                    json_text = json.dumps({"text": message_content, "color": "gray"})
                    tellraw_command = f'tellraw @a {json_text}'

                    # 发送到服务器
                    await self.sendZZKCommand(tellraw_command)
                    # 使用空结果来阻止消息继续传播
                    yield event.plain_result("")
                    return

        if (chain[0].type == "Poke:poke" and chain[0].qq == int(event.message_obj.self_id)):
            random.seed(time.time())
            randint = random.randint(0, 4)
            yield event.plain_result(poke_resp_list[randint])
        else:
            for msg in chain:
                msg_str = msg.toString()
                if (msg.type == "Plain" and ("现充" in msg_str or "线虫" in msg_str)):
                    # 发送消息
                    yield event.plain_result("线虫☹☹☹☹捅死你喵捅死你喵")
                    return
                if (msg.type == "Plain" and sender == "2627890758" and ("br" in msg_str or "方块竞速" in msg_str or "block race" in msg_str or "block racing" in msg_str)):
                    # 发送消息
                    yield event.plain_result("br大师Na2PtCl6")
                    return
                if (msg.type == "Plain" and ("🦌" in msg_str or "吉吉" in msg_str or "鹿" in msg_str)):
                    # 发送消息
                    yield event.plain_result("🦌🦌🦌🦌🦌🦌🦌🦌🦌")
                    return

            global add1reply, add1count
            # 确保chain不为空才进行后续处理
            if not chain:
                return

            if add1reply is None or len(chain) != len(add1reply):
                add1reply = chain
                add1count = 1
                return

            for idx, msg in enumerate(chain):
                if (msg.type != add1reply[idx].type):
                    add1reply = chain
                    add1count = 1
                    return
                if (msg.type == "Plain" and msg.toString() != add1reply[idx].toString()):
                    add1reply = chain
                    add1count = 1
                    return
                if (msg.type == "Image" and msg.file != add1reply[idx].file):
                    add1reply = chain
                    add1count = 1
                    return
                if (msg.type == "Face" and msg.id != add1reply[idx].id):
                    add1reply = chain
                    add1count = 1
                    return

            add1count += 1
            if add1count == 3:
                    # 发送消息
                    yield event.chain_result(chain)
                

    # mcstatus 指令组：查询服务器列表状态
    # mcstatus ad
    # mcstatus zzk
    # mcstatus offline
    @filter.command_group("mcstatus")
    def mcstatus(self):
        """获取服务器状态"""
        pass

    @mcstatus.command("rank")
    async def mcstatusRank(self, event: AstrMessageEvent):
        """获取zzk服务器玩家在线时长排行榜"""

        response = await self.getPlayerRankData()
        if response.status_code == 200:
            data = response.json()
            
            # 按今日在线时间排序，只取前5名
            sorted_players = sorted(data.items(), key=lambda x: x[1].get('today_time', 0), reverse=True)[:5]
            
            if not sorted_players:
                yield event.plain_result("暂无玩家数据。")
                return
            
            # 构建消息链，包含文本和图片
            message_chain = []
            message_chain.append(Comp.Plain("📊 今日在线时长排行榜 📊\n"))
            
            for idx, (player_name, player_data) in enumerate(sorted_players):
                # 格式化时间（秒转换为小时分钟）
                today_seconds = player_data.get('today_time', 0)
                total_seconds = player_data.get('online_time', 0)
                
                today_hours = int(today_seconds // 3600)
                today_minutes = int((today_seconds % 3600) // 60)
                
                total_hours = int(total_seconds // 3600)
                total_minutes = int((total_seconds % 3600) // 60)
                
                # 格式化为中文时间
                today_time_str = f"{today_hours}小时{today_minutes}分钟" if today_hours > 0 else f"{today_minutes}分钟"
                total_time_str = f"{total_hours}小时{total_minutes}分钟" if total_hours > 0 else f"{total_minutes}分钟"
                
                # 在线状态
                online_status = "🟢在线" if player_data.get('online', False) else "🔴离线"
                
                # 前三名特殊标记
                if idx == 0:
                    rank_symbol = "👑"
                elif idx == 1:
                    rank_symbol = "🥈"
                elif idx == 2:
                    rank_symbol = "🥉"
                else:
                    rank_symbol = f"{idx + 1}."
                
                # 获取缓存的头像（64x64分辨率）
                avatar_url = player_data.get('avatar', '')
                if avatar_url:
                    cached_avatar = self.get_cached_avatar(player_name, avatar_url)
                    message_chain.append(Comp.Image(file=cached_avatar))
                
                # 添加玩家信息
                player_info = f"{rank_symbol} {player_name} {online_status}\n"
                player_info += f"   今日: {today_time_str}\n"
                player_info += f"   总计: {total_time_str}\n"
                player_info += "─" * 25 + "\n"
                
                message_chain.append(Comp.Plain(player_info))
            
            yield event.chain_result(message_chain)
        else:
            yield event.plain_result("获取排行榜数据失败，请检查API密钥和URL配置。")

    @mcstatus.command("totalrank")
    async def mcstatusTotalRank(self, event: AstrMessageEvent):
        """获取zzk服务器玩家总累计时长卷王排行榜"""

        response = await self.getPlayerRankData()
        if response.status_code == 200:
            data = response.json()
            
            # 按总累计在线时间排序，只取前5名
            sorted_players = sorted(data.items(), key=lambda x: x[1].get('online_time', 0), reverse=True)[:5]
            
            if not sorted_players:
                yield event.plain_result("暂无玩家数据。")
                return
            
            # 构建消息链，包含文本和图片
            message_chain = []
            message_chain.append(Comp.Plain("🎯 卷王排行榜 🎯\n"))
            message_chain.append(Comp.Plain("(总累计在线时长)\n"))
            
            for idx, (player_name, player_data) in enumerate(sorted_players):
                # 格式化总累计时间
                total_seconds = player_data.get('online_time', 0)
                
                total_hours = int(total_seconds // 3600)
                total_minutes = int((total_seconds % 3600) // 60)
                
                # 格式化为中文时间
                total_time_str = f"{total_hours}小时{total_minutes}分钟" if total_hours > 0 else f"{total_minutes}分钟"
                
                # 在线状态
                online_status = "🟢在线" if player_data.get('online', False) else "🔴离线"
                
                # 前三名特殊标记
                if idx == 0:
                    rank_symbol = "👑"
                elif idx == 1:
                    rank_symbol = "🥈"
                elif idx == 2:
                    rank_symbol = "🥉"
                else:
                    rank_symbol = f"{idx + 1}."
                
                # 获取缓存的头像（64x64分辨率）
                avatar_url = player_data.get('avatar', '')
                if avatar_url:
                    cached_avatar = self.get_cached_avatar(player_name, avatar_url)
                    message_chain.append(Comp.Image(file=cached_avatar))
                
                # 添加玩家信息
                player_info = f"{rank_symbol} {player_name} {online_status}\n"
                player_info += f"   总计: {total_time_str}\n"
                player_info += "─" * 25 + "\n"
                
                message_chain.append(Comp.Plain(player_info))
            
            yield event.chain_result(message_chain)
        else:
            yield event.plain_result("获取排行榜数据失败，请检查API密钥和URL配置。")

    @mcstatus.command("zzk")
    async def mcstatusZZK(self, event: AstrMessageEvent):
        """获取zzk服务器状态"""

        response = await self.getZZKServerInfo()
        if response.status_code == 200:
            data = response.json()
            server_info = "=======================\n"
            for instance in data:
                server_name = instance["motd"]
                server_version = instance["version"]["name"]
                server_status = instance["running"]
                current_players = instance["players"]["online"]
                players_list = instance["players"]["player_list"]

                #状态映射
                status_map = {
                    True : "运行中",
                    False : "停止",
                }

                server_info += f"服务器名称: {server_name}\n"
                server_info += f"版本: {server_version}\n"
                server_info += f"状态: {status_map.get(server_status, '未知')}\n"
                server_info += f"当前在线玩家数: {current_players}\n"
                server_info += f"玩家列表: {players_list}\n"
                server_info += "=======================\n"
            yield event.plain_result(server_info)
        else:
            yield event.plain_result("获取服务器状态失败，请检查API密钥和URL配置。")
    
    @filter.permission_type(filter.PermissionType.ADMIN)
    @mcstatus.command("offline")
    async def getZZKOfflineServers(self, event: AstrMessageEvent):
        """获取zzk离线服务器状态（仅管理员可用）"""

        response = await self.getZZKOfflineServerInfo()
        if response.status_code == 200:
            data = response.json()
            server_info = "=======================\n"
            for instance in data:
                server_name = instance["motd"]
                server_version = instance["version"]["name"]

                #状态映射
                status_map = {
                    True : "运行中",
                    False : "停止",
                }

                server_info += f"服务器名称: {server_name}\n"
                server_info += f"版本: {server_version}\n"
                server_info += "=======================\n"
            yield event.plain_result(server_info)
        else:
            yield event.plain_result("获取服务器状态失败，请检查API密钥和URL配置。")
    
    @mcstatus.command("ad")
    async def mcstatusAD(self, event: AstrMessageEvent):
        """获取ad服务器状态"""

        response = await self.getADServerInfo()
        if response.status_code == 200:
            data = response.json()
            server_info = "=======================\n"
            for instance in data["data"]["data"]:
                server_name = instance["config"]["nickname"]
                server_version = instance["info"]["version"]
                server_status = instance["status"]
                current_players = instance["info"]["currentPlayers"]
                # players_list = instance["info"]["playersChart"]

                #状态映射
                status_map = {
                    -1 : "忙碌",
                    0 : "停止",
                    1 : "停止中",
                    2 : "启动中",
                    3 : "运行中"
                }

                server_info += f"服务器名称: {server_name}\n"
                server_info += f"版本: {server_version}\n"
                server_info += f"状态: {status_map.get(server_status, '未知')}\n"
                server_info += f"当前在线玩家数: {current_players}\n"
                # server_info += f"玩家列表: {players_list}\n"
                server_info += "=======================\n"
            yield event.plain_result(server_info)
        else:
            yield event.plain_result("获取服务器状态失败，请检查API密钥和URL配置。")

    # server 指令组：更改服务器状态
    # server stop
    # server start
    # server restart
    # server op
    # server deop
    @filter.command_group("server")
    def server(self):
        """更改服务器状态"""
        pass

    @server.command("stop")
    async def stopServer(self, event: AstrMessageEvent, hostName: str, serverName = ""):
        """停止指定服务器"""

        if event.get_sender_id() not in deploy_list:
            yield event.plain_result("你没有权限执行该操作。")
            return

        if hostName == "ad":
            response = await self.getADServerInfo()
            if response.status_code == 200:
                data = response.json()
                flag = False
                for instance in data["data"]["data"]:
                    if instance["config"]["nickname"] == serverName:
                        flag = True
                        if instance["status"] < 3:
                            yield event.plain_result("服务器未运行，请检查服务器状态。")
                        else:
                            # set params
                            params = {
                                'apikey': ad_apikey,
                                'daemonId': ad_daemonId,
                                'uuid': instance["instanceUuid"],
                            }

                            response = requests.get(ad_baseURL + "/api/protected_instance/stop", params = params)
                            if response.status_code == 200:
                                yield event.plain_result(f"服务器 {serverName} 停止成功。")
                            else:
                                yield event.plain_result(f"服务器 {serverName} 停止失败，请检查API密钥和URL配置。")
                            break
                if not flag:
                    yield event.plain_result(f"服务器 {serverName} 不存在，请检查服务器名称。")
            else:
                yield event.plain_result("获取服务器状态失败，请检查API密钥和URL配置。")
        elif hostName == "zzk":
            data = {
                "rcon_info": {
                    "rcon_host": "127.0.0.1",
                    "rcon_password": "142857",
                    "rcon_port": 25575,
                },
                "host": "113.44.84.175:23432"
            }

            headers = {
                'x-api-key': zzk_apikey
            }

            response = requests.post(zzk_baseURL + "/shutdown_server", json = data, headers = headers)
            if response.status_code == 200:
                yield event.plain_result(f"服务器停止成功！")
            elif response.status_code == 403:
                yield event.plain_result(f"服务器已关闭。")

    @server.command("start")
    async def startServer(self, event: AstrMessageEvent, hostName: str, serverName: str):
        """启动指定服务器"""

        if event.get_sender_id() not in deploy_list:
            yield event.plain_result("你没有权限执行该操作。")
            return

        if hostName == "ad":
            response = await self.getADServerInfo()
            if response.status_code == 200:
                data = response.json()
                flag = False
                for instance in data["data"]["data"]:
                    if instance["config"]["nickname"] == serverName:
                        flag = True
                        if instance["status"] == 3:
                            yield event.plain_result("服务器运行中，请检查服务器状态。")
                        else:
                            # set params
                            params = {
                                'apikey': ad_apikey,
                                'daemonId': ad_daemonId,
                                'uuid': instance["instanceUuid"],
                            }

                            response = requests.get(ad_baseURL + "/api/protected_instance/open", params = params)
                            if response.status_code == 200:
                                yield event.plain_result(f"服务器 {serverName} 启动成功。")
                            else:
                                yield event.plain_result(f"服务器 {serverName} 启动失败，请检查API密钥和URL配置。")
                            break
                if not flag:
                    yield event.plain_result(f"服务器 {serverName} 不存在，请检查服务器名称。")
            else:
                yield event.plain_result("获取服务器状态失败，请检查API密钥和URL配置。")
        elif hostName == "zzk":
            response = await self.getZZKOfflineServerInfo()
            data = response.json()
            flag = False
            for instance in data:
                if instance["motd"] == serverName:
                    flag = True
                    if instance["running"] == True:
                        yield event.plain_result("服务器运行中，请检查服务器状态。")
                    else:
                        # set data
                        data = {
                            "server_id": instance["id"],
                            "screen": instance["screen"],
                            "dir": instance["dir"],
                        }

                        headers = {
                            'x-api-key': zzk_apikey,
                            'Content-Type': 'application/json'
                        }

                        response = requests.post(zzk_baseURL + "/start_server", json = data, headers = headers)
                        if response.status_code == 200:
                            yield event.plain_result(f"服务器 {serverName} 启动成功！")
                        else:
                            yield event.plain_result(response.status_code)
                        break
            if not flag:
                yield event.plain_result(f"服务器 {serverName} 不存在，请检查服务器名称。")

    @server.command("restart")
    async def restartServer(self, event: AstrMessageEvent, hostName: str, serverName: str):
        """重启指定服务器"""

        if event.get_sender_id() not in deploy_list:
            yield event.plain_result("你没有权限执行该操作。")
            return

        if hostName == "ad":
            response = await self.getADServerInfo()
            if response.status_code == 200:
                data = response.json()
                flag = False
                for instance in data["data"]["data"]:
                    if instance["config"]["nickname"] == serverName:
                        flag = True
                        if instance["status"] < 3:
                            yield event.plain_result("服务器未运行，请检查服务器状态。")
                        else:
                            # set params
                            params = {
                                'apikey': ad_apikey,
                                'daemonId': ad_daemonId,
                                'uuid': instance["instanceUuid"],
                            }

                            response = requests.get(ad_baseURL + "/api/protected_instance/restart", params = params)
                            if response.status_code == 200:
                                yield event.plain_result(f"服务器 {serverName} 重启成功。")
                            else:
                                yield event.plain_result(f"服务器 {serverName} 重启失败，请检查API密钥和URL配置。")
                            break
                if not flag:
                    yield event.plain_result(f"服务器 {serverName} 不存在，请检查服务器名称。")
            else:
                yield event.plain_result("获取服务器状态失败，请检查API密钥和URL配置。")
        elif hostName == "zzk":
            response = await self.getZZKOfflineServerInfo()

    @server.command("op")
    async def grantOP(self, event: AstrMessageEvent, hostName: str, serverName: str, playerName: str):
        """授予某人OP权限"""

        if event.get_sender_id() not in op_list:
            yield event.plain_result("你没有权限执行该操作。")
            return

        if hostName == "ad":
            response = await self.getADServerInfo()
            if response.status_code == 200:
                data = response.json()
                server_info = "=======================\n"
                for instance in data["data"]["data"]:
                    if instance["config"]["nickname"] == serverName:
                        if instance["status"] < 3:
                            yield event.plain_result("服务器未运行，请检查服务器状态。")
                        else:
                            # set params
                            params = {
                                'apikey': ad_apikey,
                                'daemonId': ad_daemonId,
                                'uuid': instance["instanceUuid"],
                                'command': "op " + playerName,
                            }

                            response = requests.get(ad_baseURL + "/api/protected_instance/command", params = params)
                            if response.status_code == 200:
                                yield event.plain_result(f"成功授予玩家 {playerName} OP权限。")
                            else:
                                yield event.plain_result(f"指令发送失败，请检查API密钥和URL配置。")
                            break
            else:
                yield event.plain_result("获取服务器状态失败，请检查API密钥和URL配置。")

    @server.command("deop")
    async def removeOP(self, event: AstrMessageEvent, hostName: str, serverName: str, playerName: str):
        """撤销某人OP权限"""

        if event.get_sender_id() not in op_list:
            yield event.plain_result("你没有权限执行该操作。")
            return

        if hostName == "ad":
            response = await self.getADServerInfo()
            if response.status_code == 200:
                data = response.json()
                server_info = "=======================\n"
                for instance in data["data"]["data"]:
                    if instance["config"]["nickname"] == serverName:
                        if instance["status"] < 3:
                            yield event.plain_result("服务器未运行，请检查服务器状态。")
                        else:
                            # set params
                            params = {
                                'apikey': ad_apikey,
                                'daemonId': ad_daemonId,
                                'uuid': instance["instanceUuid"],
                                'command': "deop " + playerName,
                            }

                            response = requests.get(ad_baseURL + "/api/protected_instance/command", params = params)
                            if response.status_code == 200:
                                yield event.plain_result(f"成功撤销玩家 {playerName} OP权限。")
                            else:
                                yield event.plain_result(f"指令发送失败，请检查API密钥和URL配置。")
                            break
            else:
                yield event.plain_result("获取服务器状态失败，请检查API密钥和URL配置。")

    # perm 指令组：控制用户管理服务器权限
    # perm grant
    # perm remove
    @filter.command_group("perm")
    def perm(self):
        """更改服务器状态"""
        pass

    @filter.permission_type(filter.PermissionType.ADMIN)
    @perm.command("grant")
    async def grantPerm(self, event: AstrMessageEvent, userID: str, permType: str):
        """授予指定用户权限（仅管理员使用）：
        1. grant user deploy: 授予指定用户管理服务器的权限
        2. grant user op: 授予指定用户给予玩家OP的权限"""

        if permType != "deploy" and permType != "op":
            yield event.plain_result("权限类型错误，请检查权限类型。")
        else:
            if permType == "deploy":
                if userID in deploy_list:
                    yield event.plain_result(f"用户 {userID} 已经拥有管理服务器的权限。")
                else:
                    deploy_list.append(userID)
                    yield event.plain_result(f"向用户 {userID} 授予了管理服务器的权限。")
            elif permType == "op":
                if userID in op_list:
                    yield event.plain_result(f"用户 {userID} 已经拥有给予玩家OP的权限。")
                else:
                    op_list.append(userID)
                    yield event.plain_result(f"向用户 {userID} 授予了给予玩家OP的权限。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @perm.command("remove")
    async def removePerm(self, event: AstrMessageEvent, userID: str, permType: str):
        """撤销指定用户权限（仅管理员使用）：
        1. remove user deploy: 撤销指定用户管理服务器的权限
        2. remove user op: 撤销指定用户给予玩家OP的权限"""

        if permType != "deploy" and permType != "op":
            yield event.plain_result("权限类型错误，请检查权限类型。")
        else:
            if permType == "deploy":
                if userID not in deploy_list:
                    yield event.plain_result(f"用户 {userID} 未拥有管理服务器的权限。")
                else:
                    deploy_list.remove(userID)
                    yield event.plain_result(f"撤销了用户 {userID} 管理服务器的权限。")
            elif permType == "op":
                if userID not in op_list:
                    yield event.plain_result(f"用户 {userID} 未拥有给予玩家OP的权限。")
                else:
                    op_list.remove(userID)
                    yield event.plain_result(f"撤销了用户 {userID} 给予玩家OP的权限。")

    # player 指令组：玩家个人功能
    # player bind
    # player time
    @filter.command_group("player")
    def player(self):
        """玩家个人功能"""
        pass

    @player.command("bind")
    async def bindPlayer(self, event: AstrMessageEvent, playerName: str):
        """绑定Minecraft玩家昵称"""
        global player_bindings
        
        user_id = event.get_sender_id()
        player_bindings[user_id] = playerName
        
        yield event.plain_result(f"成功绑定玩家昵称：{playerName}")

    @player.command("time")
    async def playerTime(self, event: AstrMessageEvent):
        """查询个人在线时间"""
        global player_bindings
        
        user_id = event.get_sender_id()
        
        # 检查是否已绑定玩家
        if user_id not in player_bindings:
            yield event.plain_result("你还没有绑定Minecraft玩家昵称，请先使用 'player bind <玩家名>' 进行绑定。")
            return
        
        player_name = player_bindings[user_id]
        
        # 获取玩家数据
        response = await self.getPlayerRankData()
        if response.status_code == 200:
            data = response.json()
            
            # 查找绑定的玩家数据
            if player_name not in data:
                yield event.plain_result(f"未找到玩家 '{player_name}' 的数据，请检查玩家名是否正确。")
                return
            
            player_data = data[player_name]
            
            # 格式化时间
            today_seconds = player_data.get('today_time', 0)
            total_seconds = player_data.get('online_time', 0)
            
            today_hours = int(today_seconds // 3600)
            today_minutes = int((today_seconds % 3600) // 60)
            
            total_hours = int(total_seconds // 3600)
            total_minutes = int((total_seconds % 3600) // 60)
            
            # 格式化为中文时间
            today_time_str = f"{today_hours}小时{today_minutes}分钟" if today_hours > 0 else f"{today_minutes}分钟"
            total_time_str = f"{total_hours}小时{total_minutes}分钟" if total_hours > 0 else f"{total_minutes}分钟"
            
            # 在线状态
            online_status = "🟢在线" if player_data.get('online', False) else "🔴离线"
            
            # 构建消息链
            message_chain = []
            
            # 添加头像
            avatar_url = player_data.get('avatar', '')
            if avatar_url:
                cached_avatar = self.get_cached_avatar(player_name, avatar_url)
                message_chain.append(Comp.Image(file=cached_avatar))
            
            # 添加个人信息
            player_info = f"👤 {player_name} {online_status}\n"
            player_info += f"📅 今日在线: {today_time_str}\n"
            player_info += f"⏰ 总累计: {total_time_str}"
            
            message_chain.append(Comp.Plain(player_info))
            
            yield event.chain_result(message_chain)
        else:
            yield event.plain_result("获取玩家数据失败，请检查API配置。")

    async def sendZZKCommand(self, command: str):
        """向ZZK服务器发送指令"""
        data = {
            "rcon_info": {
                "rcon_host": "127.0.0.1",
                "rcon_password": "142857",
                "rcon_port": 25575,
            },
            "command": command
        }

        headers = {
            'x-api-key': zzk_apikey,
            'Content-Type': 'application/json'
        }

        response = requests.post(zzk_baseURL + "/send_command", json=data, headers=headers)
        return response

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handleSayCommand(self, event: AstrMessageEvent):
        """处理say指令"""
        chain = event.get_messages()

        if not chain or len(chain) == 0:
            return

        # 提取所有Plain文本内容，跳过At组件
        text_parts = []
        for msg in chain:
            if msg.type == "Plain":
                text_parts.append(msg.toString())

        if not text_parts:
            return

        # 合并所有文本内容并去除多余空格
        full_text = ' '.join(text_parts).strip()

        if not full_text.startswith("say "):
            return

        # 提取say指令后的内容
        say_content = full_text[4:]  # 移除"say "前缀

        if not say_content:
            yield event.plain_result("请提供要说的内容。")
            return

        # 构建minecraft say指令
        minecraft_command = f'say "{say_content}"'

        # 发送指令
        response = await self.sendZZKCommand(minecraft_command)

        if response.status_code == 200:
            yield event.plain_result(f"成功在服务器发送消息：{say_content}")
        elif response.status_code == 403:
            response_data = response.json()
            yield event.plain_result(f"发送失败：{response_data.get('message', '服务器错误')}")
        else:
            yield event.plain_result("发送失败，请检查服务器状态。")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handleCmdCommand(self, event: AstrMessageEvent):
        """处理cmd指令"""
        chain = event.get_messages()

        if not chain or len(chain) == 0:
            return

        # 提取所有Plain文本内容，跳过At组件
        text_parts = []
        for msg in chain:
            if msg.type == "Plain":
                text_parts.append(msg.toString())

        if not text_parts:
            return

        # 合并所有文本内容并去除多余空格
        full_text = ' '.join(text_parts).strip()

        if not full_text.startswith("cmd "):
            return

        if event.get_sender_id() not in deploy_list:
            yield event.plain_result("你没有权限执行该操作。")
            return

        # 提取cmd指令后的内容
        cmd_content = full_text[4:]  # 移除"cmd "前缀

        if not cmd_content:
            yield event.plain_result("请提供要执行的指令。")
            return

        # 发送指令
        response = await self.sendZZKCommand(cmd_content)

        if response.status_code == 200:
            yield event.plain_result(f"成功执行指令：{cmd_content}")
        elif response.status_code == 403:
            response_data = response.json()
            yield event.plain_result(f"执行失败：{response_data.get('message', '服务器错误')}")
        else:
            yield event.plain_result("执行失败，请检查服务器状态。")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        global polling_task
        if polling_task and not polling_task.done():
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
