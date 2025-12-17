"""Quick test script to verify configuration loads properly"""
import yaml
from pathlib import Path
import sys

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def test_config():
    config_file = Path("config/config.yaml")

    print("Testing configuration...")
    print(f"Config file exists: {config_file.exists()}")

    if not config_file.exists():
        print("ERROR: Config file not found!")
        return False

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        print("SUCCESS: Config file loaded successfully")

        # Check agents configuration
        agents = config.get("agents", {})
        print(f"\nAgents configuration:")

        for agent_name, agent_config in agents.items():
            enabled = agent_config.get("enabled", False)
            status = "ENABLED" if enabled else "DISABLED"
            tools = agent_config.get("tools", [])
            print(f"  {agent_name:20} {status:12} tools: {tools}")

        # Check which agents are enabled
        enabled_agents = [name for name, cfg in agents.items() if cfg.get("enabled", False)]
        print(f"\n{len(enabled_agents)} agents enabled: {', '.join(enabled_agents)}")

        # Check MCP servers
        mcp_servers = config.get("mcp_servers", {})
        enabled_servers = [name for name, cfg in mcp_servers.items() if cfg.get("enabled", False)]
        print(f"{len(enabled_servers)} MCP servers enabled: {', '.join(enabled_servers)}")

        return True

    except Exception as e:
        print(f"❌ Error loading config: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_config()
    exit(0 if success else 1)
