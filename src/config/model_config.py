"""
模型配置文件
根据不同场景和硬件配置优化模型选择
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import os

@dataclass
class ModelRecommendation:
    """模型推荐配置"""
    scenario: str
    description: str
    llm_models: List[str]
    ml_models: List[str]
    dl_models: List[str]
    weights: Dict[str, float]
    hardware_requirement: Dict[str, str]
    expected_performance: Dict[str, str]

# 预设模型配置
MODEL_CONFIGS = {
    "budget_conscious": ModelRecommendation(
        scenario="budget_conscious",
        description="预算优先 - 最小硬件需求",
        llm_models=["phi3:medium"],  # 4bit量化
        ml_models=["xgboost", "random_forest"],
        dl_models=[],  # 不使用深度学习模型
        weights={"llm": 0.5, "ml": 0.5, "dl": 0.0},
        hardware_requirement={
            "memory": "8GB",
            "storage": "20GB",
            "cpu": "4核"
        },
        expected_performance={
            "speed": "快速 (2-5秒)",
            "accuracy": "良好 (70-80%)",
            "cost": "最低"
        }
    ),

    "balanced": ModelRecommendation(
        scenario="balanced",
        description="平衡配置 - 性能与成本最优",
        llm_models=["qwen2.5:7b"],
        ml_models=["xgboost", "random_forest"],
        dl_models=["gru"],
        weights={"llm": 0.4, "ml": 0.35, "dl": 0.25},
        hardware_requirement={
            "memory": "16GB",
            "storage": "50GB",
            "cpu": "6核"
        },
        expected_performance={
            "speed": "中等 (3-7秒)",
            "accuracy": "优秀 (80-90%)",
            "cost": "中等"
        }
    ),

    "performance": ModelRecommendation(
        scenario="performance",
        description="性能优先 - 最高精度",
        llm_models=["qwen2.5:14b", "llama3.1:8b"],
        ml_models=["xgboost", "lightgbm", "random_forest"],
        dl_models=["gru", "lstm", "transformer"],
        weights={"llm": 0.35, "ml": 0.35, "dl": 0.30},
        hardware_requirement={
            "memory": "32GB+",
            "storage": "100GB+",
            "cpu": "8核+",
            "gpu": "RTX 3080+"
        },
        expected_performance={
            "speed": "快速 (2-4秒)",
            "accuracy": "极优 (90-95%)",
            "cost": "高"
        }
    ),

    "high_frequency": ModelRecommendation(
        scenario="high_frequency",
        description="高频交易 - 极速响应",
        llm_models=["llama3.1:8b"],
        ml_models=["lightgbm"],
        dl_models=["gru"],
        weights={"llm": 0.25, "ml": 0.45, "dl": 0.30},
        hardware_requirement={
            "memory": "16GB",
            "storage": "50GB SSD",
            "cpu": "8核",
            "gpu": "RTX 3080+"
        },
        expected_performance={
            "speed": "极速 (1-3秒)",
            "accuracy": "良好 (75-85%)",
            "cost": "中高"
        }
    )
}

def get_model_config(scenario: str) -> Optional[ModelRecommendation]:
    """获取模型配置"""
    return MODEL_CONFIGS.get(scenario)

def recommend_config_by_hardware() -> str:
    """根据硬件配置推荐方案"""
    # 检测硬件 (简化版)
    memory_gb = 8  # 默认值

    # 读取系统内存 (Linux/macOS)
    try:
        if os.name == 'posix':
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        memory_kb = int(line.split()[1])
                        memory_gb = memory_kb / 1024 / 1024
                        break
    except:
        pass

    # 根据内存推荐
    if memory_gb < 12:
        return "budget_conscious"
    elif memory_gb < 24:
        return "balanced"
    else:
        return "performance"

def get_ollama_install_commands(scenario: str) -> List[str]:
    """获取Ollama安装命令"""
    config = get_model_config(scenario)
    if not config:
        return []

    commands = []

    # 基础安装
    commands.append("curl -fsSL https://ollama.ai/install.sh | sh")

    # 模型安装
    commands.append(f"# 安装推荐模型 ({scenario})")
    for model in config.llm_models:
        commands.append(f"ollama pull {model}")

    return commands

def generate_model_check_script(scenario: str) -> str:
    """生成模型检查脚本"""
    config = get_model_config(scenario)
    if not config:
        return ""

    script = f"""#!/bin/bash
# 模型检查脚本 ({scenario})

echo "🔍 检查模型配置: {scenario}"
echo "硬件需求: {config.hardware_requirement}"
echo

# 检查Ollama服务
if ! pgrep -x "ollama" > /dev/null; then
    echo "❌ Ollama服务未运行"
    echo "启动命令: ollama serve"
    exit 1
fi

echo "✅ Ollama服务运行中"

# 检查模型
echo "📋 检查模型状态..."
ollama list

# 测试模型响应
echo "🧪 测试模型响应..."
echo "测试模型: {config.llm_models[0] if config.llm_models else 'N/A'}"

if [ -n "{config.llm_models[0] if config.llm_models else ''}" ]; then
    timeout 30 ollama run {config.llm_models[0]} "你好，请回复'模型正常'" 2>/dev/null
fi

echo "✅ 检查完成"
"""

    return script

def get_training_config(scenario: str) -> Dict:
    """获取训练配置"""
    config = get_model_config(scenario)
    if not config:
        return {}

    training_configs = {
        "budget_conscious": {
            "xgboost": {
                "n_estimators": 50,
                "max_depth": 4,
                "learning_rate": 0.1
            },
            "gru": None,  # 不使用
        },
        "balanced": {
            "xgboost": {
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.05
            },
            "gru": {
                "units": 32,
                "epochs": 10,
                "batch_size": 32
            }
        },
        "performance": {
            "xgboost": {
                "n_estimators": 200,
                "max_depth": 8,
                "learning_rate": 0.03
            },
            "gru": {
                "units": 64,
                "epochs": 20,
                "batch_size": 64
            },
            "lstm": {
                "units": 64,
                "epochs": 20,
                "batch_size": 64
            }
        }
    }

    return training_configs.get(scenario, {})

def print_config_summary():
    """打印配置摘要"""
    print("=" * 80)
    print("🎯 模型配置摘要")
    print("=" * 80)
    print()

    for scenario, config in MODEL_CONFIGS.items():
        print(f"📦 {scenario}")
        print(f"   {config.description}")
        print(f"   内存需求: {config.hardware_requirement.get('memory', 'N/A')}")
        print(f"   LLM模型: {config.llm_models}")
        print(f"   性能: {config.expected_performance.get('speed', 'N/A')}")
        print()

# 使用示例
if __name__ == "__main__":
    # 打印所有配置
    print_config_summary()

    # 根据硬件推荐
    recommended = recommend_config_by_hardware()
    print(f"💡 根据您的硬件配置，推荐方案: {recommended}")
    print()

    # 获取配置
    config = get_model_config(recommended)
    if config:
        print("📋 推荐配置详情:")
        print(f"  场景: {config.scenario}")
        print(f"  描述: {config.description}")
        print(f"  LLM模型: {config.llm_models}")
        print(f"  ML模型: {config.ml_models}")
        print(f"  权重: {config.weights}")
        print()

        print("🛠️ 安装命令:")
        for cmd in get_ollama_install_commands(recommended):
            print(f"  {cmd}")
        print()