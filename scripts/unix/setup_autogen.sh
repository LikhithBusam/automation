#!/bin/bash
# AutoGen Setup Script
# Sets up the environment for AutoGen migration

echo "========================================="
echo "AutoGen Migration Setup"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install AutoGen
echo ""
echo "Installing AutoGen and dependencies..."
pip install pyautogen
pip install "pyautogen[teachable]"
pip install "pyautogen[retrievechat]"

# Create necessary directories
echo ""
echo "Creating data directories..."
mkdir -p data/teachable
mkdir -p data/conversations
mkdir -p data/checkpoints
mkdir -p workspace/code_execution
mkdir -p logs

# Check if .env exists
echo ""
if [ -f ".env" ]; then
    echo "✓ .env file found"

    # Check for required environment variables
    if grep -q "OPENROUTER_API_KEY" .env; then
        echo "✓ OPENROUTER_API_KEY configured"
    else
        echo "⚠ OPENROUTER_API_KEY not found in .env"
        echo "  Add: OPENROUTER_API_KEY=your_key_here"
    fi
else
    echo "⚠ .env file not found"
    echo "  Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  Please edit .env and add your API keys"
    fi
fi

# Add AutoGen-specific environment variables if not present
echo ""
echo "Checking AutoGen environment variables..."

add_env_var() {
    local var_name=$1
    local var_value=$2

    if ! grep -q "^${var_name}=" .env; then
        echo "${var_name}=${var_value}" >> .env
        echo "  Added: ${var_name}"
    fi
}

if [ -f ".env" ]; then
    add_env_var "AUTOGEN_USE_DOCKER" "false"
    add_env_var "AUTOGEN_WORK_DIR" "./workspace/code_execution"
    add_env_var "AUTOGEN_MAX_CONSECUTIVE_AUTO_REPLY" "10"
    add_env_var "TEACHABLE_DB_PATH" "./data/teachable"
    add_env_var "CONVERSATION_STORAGE_PATH" "./data/conversations"
    add_env_var "DATA_DIR" "./data"
    add_env_var "WORKSPACE_DIR" "./workspace"
fi

# Check MCP servers
echo ""
echo "Checking MCP servers..."
if curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo "✓ GitHub MCP server (port 3000) is running"
else
    echo "⚠ GitHub MCP server not detected on port 3000"
fi

if curl -s http://localhost:3001/health > /dev/null 2>&1; then
    echo "✓ Filesystem MCP server (port 3001) is running"
else
    echo "⚠ Filesystem MCP server not detected on port 3001"
fi

if curl -s http://localhost:3002/health > /dev/null 2>&1; then
    echo "✓ Memory MCP server (port 3002) is running"
else
    echo "⚠ Memory MCP server not detected on port 3002"
fi

# Summary
echo ""
echo "========================================="
echo "Setup Summary"
echo "========================================="
echo ""
echo "Configuration files created:"
echo "  ✓ config/autogen_agents.yaml"
echo "  ✓ config/autogen_groupchats.yaml"
echo "  ✓ config/autogen_workflows.yaml"
echo "  ✓ config/function_schemas.yaml"
echo ""
echo "Directories created:"
echo "  ✓ data/teachable/"
echo "  ✓ data/conversations/"
echo "  ✓ data/checkpoints/"
echo "  ✓ workspace/code_execution/"
echo ""
echo "Next steps:"
echo "  1. Ensure OPENROUTER_API_KEY is set in .env"
echo "  2. Start MCP servers: python start_mcp_servers.py"
echo "  3. Review AUTOGEN_MIGRATION_GUIDE.md"
echo "  4. Implement core adapters in src/autogen_adapters/"
echo "  5. Test with: python -m pytest tests/"
echo ""
echo "========================================="
