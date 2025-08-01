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
import astrbot.api.message_components as Comp

zzk_apikey = "yTOgiQlDc7o66hSRgH9Yl2FVWL0c3iUp6ftVSFxu3k1IFfgXGM68hqYupjFhjzks"
zzk_baseURL = "http://113.44.84.175:5000"
ad_apikey = "ea7d6c0032c2452aa5fc4bf53f354e62"
ad_baseURL = "http://118.89.121.81:23333"
ad_daemonId = "95192e40c67a430cb3f3944f2b87feba"

poke_resp_list = ["喵~", "我喜欢你~", "uwu", "(*╹▽╹*)", "猫猫飞扑！"]

deploy_list = ["1977741520", "1557758223"]
op_list = ["1977741520", "1557758223"]

add1reply = None
add1count = 0

@register("mcsm_automanagement", "AInfinity_LilacDream", "MC服务器智能管理群助手", "1.0.0")
class MyPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

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
        if (chain[0].type == "Poke:poke" and chain[0].qq == int(event.message_obj.self_id)):
            random.seed(time.time())
            randint = random.randint(0, 4)
            yield event.plain_result(poke_resp_list[randint])
        else:
            for msg in chain:
                str = msg.toString()
                if (msg.type == "Plain" and ("现充" in str or "线虫" in str)):
                    # 发送消息
                    yield event.plain_result("线虫☹☹☹☹捅死你喵捅死你喵")
                    return
                if (msg.type == "Plain" and sender == "2627890758" and ("br" in str or "方块竞速" in str or "block race" in str or "block racing" in str)):
                    # 发送消息
                    yield event.plain_result("br大师Na2PtCl6")
                    return
                if (msg.type == "Plain" and ("🦌" in str or "吉吉" in str or "鹿" in str)):
                    # 发送消息
                    yield event.plain_result("🦌🦌🦌🦌🦌🦌🦌🦌🦌")
                    return
                
            global add1reply, add1count
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

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
