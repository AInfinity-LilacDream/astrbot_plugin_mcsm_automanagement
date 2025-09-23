# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AstrBot plugin for managing Minecraft servers through a Discord/QQ bot interface. The plugin connects to two different Minecraft server management systems (ZZK and AD) via their APIs to monitor and control server status.

## Architecture

- **Main Plugin File**: `main.py` - Contains the core plugin class `MyPlugin` that inherits from AstrBot's `Star` base class
- **Plugin Registration**: Uses `@register("mcsm_automanagement", "AInfinity_LilacDream", "MC服务器智能管理群助手", "1.0.0")` decorator
- **Event System**: Uses AstrBot's filter decorators for message handling and command routing
- **API Integration**: Two server management APIs:
  - ZZK API (http://113.44.84.175:5000) - Custom server management
  - AD API (http://118.89.121.81:23333) - MCSM (Minecraft Server Manager) integration

## Key Components

### Server Management APIs
- **ZZK Server Management** (`main.py:37-51`): Functions for getting online/offline server info
- **AD Server Management** (`main.py:53-71`): Functions for MCSM server management
- **Permission System**: Two permission lists - `deploy_list` and `op_list` for access control

### Command Groups
1. **mcstatus** - Server status queries:
   - `mcstatus zzk` - ZZK server status
   - `mcstatus ad` - AD/MCSM server status  
   - `mcstatus offline` - Offline servers (admin only)

2. **server** - Server control operations:
   - `server start/stop/restart <hostName> <serverName>`
   - `server op/deop <hostName> <serverName> <playerName>`

3. **perm** - Permission management (admin only):
   - `perm grant/remove <userID> <permType>`

### Message Handlers
- **LLM Integration** (`main.py:73-92`): Modifies AI responses with greeting tags
- **Interactive Features** (`main.py:94-146`): Poke responses, keyword reactions, message repeating

## Development Commands

### Python Environment
- **Python Version**: 3.12.6
- **Package Manager**: pip 25.1.1
- **Install Dependencies**: `pip install -r requirements.txt` (if requirements.txt exists)

### Testing Plugin
Since this is an AstrBot plugin, testing requires the AstrBot framework. The plugin should be placed in the AstrBot plugins directory and loaded through the bot's plugin system.

### Code Style
- Uses async/await patterns extensively
- Event-driven architecture with decorators
- Follows AstrBot plugin conventions
- API keys and endpoints are hardcoded (should be moved to config for production)

## Important Notes

- **Security**: API keys are currently hardcoded in `main.py:14-18` - these should be moved to environment variables or config files
- **Permissions**: User IDs in `deploy_list` and `op_list` are hardcoded - consider database storage for persistence
- **Error Handling**: Basic HTTP status code checking is implemented
- **Async Operations**: All message handlers and API calls use async/await

## Plugin Metadata

Defined in `metadata.yaml`:
- Name: mcsm_automanagement
- Version: v1.1  
- Author: AInfinity_LilacDream
- Repository: https://github.com/AInfinity-LilacDream/astrbot_plugin_mcsm_automanagement