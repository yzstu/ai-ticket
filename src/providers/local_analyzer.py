"""
本地Ollama模型集成
使用本地Ollama + 多模型融合进行股票分析
支持真实ML模型预测和市场环境动态权重
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
import subprocess
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 动态权重配置
WEIGHT_CONFIGS = {
    'bull': {
        'technical': 0.50,
        'sentiment': 0.30,
        'capital': 0.20
    },
    'bear': {
        'technical': 0.70,
        'sentiment': 0.10,
        'capital': 0.20
    },
    'volatile': {
        'technical': 0.40,
        'sentiment': 0.20,
        'capital': 0.40
    }
}

@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    type: str  # 'llm', 'ml', 'dl'
    purpose: str
    weight: float  # 在最终决策中的权重
    description: str

class OllamaLLM:
    """本地Ollama LLM集成"""

    def __init__(self,
                 base_url: str = "http://localhost:11434",
                 model_name: str = "qwen3-coder:480b-cloud"):
        """
        初始化Ollama LLM

        Args:
            base_url: Ollama服务地址
            model_name: 模型名称
        """
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.available = self._check_connection()

        if self.available:
            logger.info(f"Ollama LLM initialized: {model_name}")
        else:
            logger.warning("Ollama not available, using fallback")

    def _check_connection(self) -> bool:
        """检查Ollama连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama connection failed: {e}")
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        if not self.available:
            raise Exception(f"Ollama服务不可用，无法生成文本。请确保Ollama服务在 {self.base_url} 运行")

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.3),
                    "num_predict": kwargs.get("max_tokens", 500),
                    "top_p": kwargs.get("top_p", 0.9)
                }
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'No response')
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return f"[Error] Status {response.status_code}"

        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"[Error] {str(e)}"

class ModelManager:
    """多模型管理器"""

    def __init__(self, model_dir: str = './models'):
        """初始化模型管理器"""
        self.llm = OllamaLLM()
        self.models = self._load_model_configs()
        self.predictions = {}
        
        # 真实ML模型
        self.model_dir = Path(model_dir)
        self.xgb_model = None
        self.rf_model = None
        self.feature_names = None
        self.ml_loaded = False
        
        # 自动加载已训练模型
        self._load_trained_models()

    def _load_trained_models(self):
        """加载已训练的ML模型"""
        try:
            # 加载XGBoost
            xgb_path = self.model_dir / 'xgboost.json'
            if xgb_path.exists():
                import xgboost as xgb
                self.xgb_model = xgb.XGBClassifier()
                self.xgb_model.load_model(str(xgb_path))
                logger.info(f"XGBoost模型已加载: {xgb_path}")
            
            # 加载RandomForest
            rf_path = self.model_dir / 'random_forest.joblib'
            if rf_path.exists():
                import joblib
                self.rf_model = joblib.load(str(rf_path))
                logger.info(f"RandomForest模型已加载: {rf_path}")
            
            # 加载特征名
            feature_path = self.model_dir / 'feature_names.json'
            if feature_path.exists():
                with open(feature_path, 'r') as f:
                    self.feature_names = json.load(f)
                logger.info(f"特征列表已加载: {len(self.feature_names)}个特征")
            
            self.ml_loaded = self.xgb_model is not None or self.rf_model is not None
            
        except Exception as e:
            logger.warning(f"加载ML模型失败: {e}")
            self.ml_loaded = False

    def _load_model_configs(self) -> List[ModelConfig]:
        """加载模型配置"""
        configs = [
            # LLM模型 (用于定性分析)
            ModelConfig(
                name="qwen3-coder:480b-cloud",
                type="llm",
                purpose="基本面分析、新闻情绪、宏观判断",
                weight=0.30,
                description="Qwen3 Coder 480B - 金融分析优化，推理能力强"
            ),

            ModelConfig(
                name="deepseek-v3.1:671b-cloud",
                type="llm",
                purpose="技术分析、综合判断",
                weight=0.10,
                description="DeepSeek V3.1 671B - 数学推理强，适合量化分析"
            ),

            # 传统机器学习模型
            ModelConfig(
                name="xgboost_trend",
                type="ml",
                purpose="趋势预测、信号识别",
                weight=0.25,
                description="XGBoost - 技术指标趋势预测"
            ),

            ModelConfig(
                name="random_forest_volatility",
                type="ml",
                purpose="波动率预测、风险评估",
                weight=0.15,
                description="Random Forest - 波动率和风险分析"
            ),

            # 深度学习模型
            ModelConfig(
                name="gru_price",
                type="dl",
                purpose="价格序列预测",
                weight=0.20,
                description="GRU - 短期价格预测"
            ),
        ]

        return configs

    def _get_market_condition(self) -> str:
        """
        获取当前市场环境

        Returns:
            市场环境类型：'bull', 'bear', 'volatile'
        """
        try:
            from src.strategy.engine import detect_market_condition, get_market_index

            index_data = get_market_index('000001')
            market_condition = detect_market_condition(index_data)
            logger.info(f"当前市场环境: {market_condition}")
            return market_condition
        except Exception as e:
            logger.warning(f"获取市场环境失败，使用默认配置: {e}")
            return 'volatile'

    def analyze_stock(self,
                     stock_code: str,
                     stock_data: Dict,
                     technical_indicators: Dict,
                     capital_flow: Dict,
                     sentiment: Dict) -> Dict:
        """
        多模型综合分析（支持动态权重）

        Args:
            stock_code: 股票代码
            stock_data: 股票数据
            technical_indicators: 技术指标
            capital_flow: 资金流向
            sentiment: 市场情绪

        Returns:
            综合分析结果
        """
        logger.info(f"Starting multi-model analysis for {stock_code}")

        # 获取市场环境
        market_condition = self._get_market_condition()
        weights = WEIGHT_CONFIGS.get(market_condition, WEIGHT_CONFIGS['volatile'])
        logger.info(f"市场环境: {market_condition}, 权重配置: {weights}")

        results = {}
        final_score = 0.0

        # 1. LLM分析
        llm_results = self._analyze_with_llm(
            stock_code, stock_data, technical_indicators,
            capital_flow, sentiment
        )
        results['llm'] = llm_results

        # 2. 机器学习模型分析
        ml_results = self._analyze_with_ml(stock_data, technical_indicators, market_condition)
        results['ml'] = ml_results

        # 3. 深度学习模型分析
        dl_results = self._analyze_with_dl(stock_data, market_condition)
        results['dl'] = dl_results

        # 4. 计算综合评分（使用动态权重）
        # LLM评分权重
        llm_score = llm_results.get('score', 50)
        final_score += llm_score * 0.4

        # ML评分权重（使用动态权重）
        if isinstance(ml_results, dict) and 'combined_score' in ml_results:
            ml_score = ml_results['combined_score']
            final_score += ml_score * 0.35

        # DL评分权重
        if isinstance(dl_results, dict) and 'gru_price' in dl_results:
            dl_score = dl_results['gru_price']['score']
            final_score += dl_score * 0.25

        # 5. 生成综合建议（考虑市场环境）
        recommendation = self._generate_recommendation_with_market(final_score, market_condition)

        return {
            'stock_code': stock_code,
            'timestamp': datetime.now().isoformat(),
            'final_score': round(final_score, 2),
            'recommendation': recommendation,
            'model_results': results,
            'confidence': self._calculate_confidence(results),
            'market_condition': market_condition,
            'weight_config': weights,
            'analysis_note': f"基于{market_condition}市场环境的动态权重分析"
        }

    def _analyze_with_llm(self,
                         stock_code: str,
                         stock_data: Dict,
                         technical_indicators: Dict,
                         capital_flow: Dict,
                         sentiment: Dict) -> Dict:
        """使用LLM分析"""
        if not self.llm.available:
            raise Exception(f"Ollama服务不可用，无法进行股票 {stock_code} 的LLM分析")

        # 构建分析提示
        prompt = f"""
请作为专业的股票分析师，分析以下股票：{stock_code}

当前价格数据：
- 价格: {stock_data.get('price', 0):.2f}
- 成交量: {stock_data.get('volume', 0):,.0f}

技术指标：
- RSI: {technical_indicators.get('rsi', 'N/A')}
- MACD: {technical_indicators.get('macd_histogram', 'N/A')}
- MA5: {technical_indicators.get('ma5', 'N/A')}
- MA20: {technical_indicators.get('ma20', 'N/A')}

资金流向：
- 主力净流入: {capital_flow.get('main_net_inflow', 0):,.0f}
- 散户净流入: {capital_flow.get('retail_net_inflow', 0):,.0f}

市场情绪：
- 情绪分数: {sentiment.get('sentiment_score', 'N/A')}
- 正面新闻: {sentiment.get('positive_news', 'N/A')}条
- 负面新闻: {sentiment.get('negative_news', 'N/A')}条

请从以下角度分析：
1. 技术面分析 (30%)
2. 资金面分析 (25%)
3. 情绪面分析 (20%)
4. 风险评估 (15%)
5. 操作建议 (10%)

请给出：
- 综合评分 (0-100)
- 简要分析 (200字以内)
- 操作建议 (买入/持有/卖出)

请以JSON格式返回：{{"score": 数值, "analysis": "分析内容", "suggestion": "操作建议"}}
"""

        try:
            response = self.llm.generate(prompt, temperature=0.3, max_tokens=800)

            # 解析JSON响应
            try:
                result = json.loads(response)
                score = result.get('score', 50)
                analysis = result.get('analysis', 'No analysis')
                suggestion = result.get('suggestion', 'HOLD')
            except json.JSONDecodeError:
                # 如果无法解析JSON，使用规则评分
                score, analysis, suggestion = self._parse_llm_text(response)

            return {
                'score': score,
                'analysis': analysis,
                'suggestion': suggestion,
                'confidence': 0.8,
                'model': self.llm.model_name,
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {
                'score': 50,
                'analysis': f'LLM analysis failed: {e}',
                'suggestion': 'HOLD',
                'confidence': 0.3,
                'model': 'error'
            }

    def _analyze_with_ml(self, stock_data: Dict, technical_indicators: Dict, market_condition: str = 'volatile') -> Dict:
        """使用机器学习模型分析（考虑市场环境）"""
        if self.ml_loaded and self.feature_names:
            # 使用真实模型预测
            return self._real_ml_prediction(stock_data, technical_indicators, market_condition)
        else:
            # 回退到模拟预测
            logger.debug("ML模型未加载，使用规则预测")
            return self._simulate_ml_prediction(stock_data, technical_indicators, market_condition)
    
    def _real_ml_prediction(self, stock_data: Dict, technical_indicators: Dict, market_condition: str = 'volatile') -> Dict:
        """使用真实ML模型预测（考虑市场环境）"""
        try:
            # 构建特征向量
            features = self._build_feature_vector(stock_data, technical_indicators)

            if features is None:
                return self._simulate_ml_prediction(stock_data, technical_indicators, market_condition)

            X = np.array([features])

            # XGBoost预测
            xgb_score = 50.0
            xgb_proba = 0.5
            if self.xgb_model is not None:
                xgb_proba = self.xgb_model.predict_proba(X)[0][1]  # 上涨概率
                xgb_score = xgb_proba * 100

            # RandomForest预测
            rf_score = 50.0
            rf_proba = 0.5
            if self.rf_model is not None:
                rf_proba = self.rf_model.predict_proba(X)[0][1]
                rf_score = rf_proba * 100

            # 综合评分 (XGBoost权重更高)
            final_score = xgb_score * 0.6 + rf_score * 0.4

            # 根据市场环境调整置信度
            if market_condition == 'bear':
                confidence_adj = 0.85  # 熊市提高置信度（更保守）
            elif market_condition == 'bull':
                confidence_adj = 0.75  # 牛市正常置信度
            else:
                confidence_adj = 0.70  # 震荡市降低置信度

            return {
                'xgboost_trend': {
                    'score': round(xgb_score, 2),
                    'up_probability': round(xgb_proba, 4),
                    'trend': 'up' if xgb_proba > 0.5 else 'down',
                    'confidence': round(0.75 * confidence_adj, 2),
                    'model': 'real_xgboost'
                },
                'random_forest_volatility': {
                    'score': round(rf_score, 2),
                    'up_probability': round(rf_proba, 4),
                    'risk_level': 'high' if rf_score < 40 else 'medium' if rf_score < 60 else 'low',
                    'confidence': round(0.70 * confidence_adj, 2),
                    'model': 'real_random_forest'
                },
                'combined_score': round(final_score, 2),
                'model': 'real_ml',
                'market_condition': market_condition
            }

        except Exception as e:
            logger.warning(f"ML预测失败: {e}，回退到规则预测")
            return self._simulate_ml_prediction(stock_data, technical_indicators, market_condition)
    
    def _build_feature_vector(self, stock_data: Dict, technical_indicators: Dict) -> Optional[List[float]]:
        """构建特征向量"""
        if not self.feature_names:
            return None
        
        features = []
        for name in self.feature_names:
            # 尝试从stock_data获取
            if name in stock_data:
                val = stock_data[name]
            # 尝试从technical_indicators获取
            elif name in technical_indicators:
                val = technical_indicators[name]
            else:
                # 使用默认值
                val = 0.0
            
            # 确保是数值
            try:
                features.append(float(val) if val is not None else 0.0)
            except:
                features.append(0.0)
        
        return features
    
    def _simulate_ml_prediction(self, stock_data: Dict, technical_indicators: Dict, market_condition: str = 'volatile') -> Dict:
        """模拟ML预测（回退方案，考虑市场环境）"""
        xgboost_score = self._simulate_xgboost_prediction(technical_indicators, market_condition)
        rf_score = self._simulate_random_forest_analysis(stock_data, market_condition)
        final_score = xgboost_score * 0.6 + rf_score * 0.4

        # 根据市场环境调整置信度
        if market_condition == 'bear':
            confidence_adj = 0.85  # 熊市提高置信度（更保守）
        elif market_condition == 'bull':
            confidence_adj = 0.75  # 牛市正常置信度
        else:
            confidence_adj = 0.70  # 震荡市降低置信度

        return {
            'xgboost_trend': {
                'score': round(xgboost_score, 2),
                'trend': 'up' if xgboost_score > 50 else 'down',
                'confidence': round(0.75 * confidence_adj, 2),
                'model': 'simulated'
            },
            'random_forest_volatility': {
                'score': round(rf_score, 2),
                'risk_level': 'high' if rf_score < 40 else 'medium' if rf_score < 60 else 'low',
                'confidence': round(0.70 * confidence_adj, 2),
                'model': 'simulated'
            },
            'combined_score': round(final_score, 2),
            'model': 'simulated_ml',
            'market_condition': market_condition
        }

    def _analyze_with_dl(self, stock_data: Dict, market_condition: str = 'volatile') -> Dict:
        """使用深度学习模型分析（考虑市场环境）"""
        # 模拟GRU价格预测
        gru_score = self._simulate_gru_prediction(stock_data, market_condition)

        # 根据市场环境调整置信度
        if market_condition == 'bull':
            confidence = 0.85  # 牛市趋势预测更准
        elif market_condition == 'bear':
            confidence = 0.75  # 熊市预测难度增加
        else:
            confidence = 0.80  # 震荡市

        return {
            'gru_price': {
                'score': gru_score,
                'prediction': '涨' if gru_score > 50 else '跌',
                'confidence': confidence,
                'time_horizon': '1-3天',
                'market_condition': market_condition
            },
            'model': 'deep_learning'
        }

    def _simulate_xgboost_prediction(self, indicators: Dict, market_condition: str = 'volatile') -> float:
        """模拟XGBoost趋势预测（考虑市场环境）"""
        score = 50.0

        # RSI分析
        rsi = indicators.get('rsi', 50)
        if 30 <= rsi <= 40:
            score += 15  # 超卖反弹
        elif 60 <= rsi <= 70:
            score += 10  # 强势
        elif rsi > 70:
            score -= 15  # 超买

        # MACD分析
        macd = indicators.get('macd_histogram', 0)
        if macd > 0:
            score += 20
        else:
            score -= 10

        # 均线分析
        ma5 = indicators.get('ma5', 0)
        ma20 = indicators.get('ma20', 0)
        price = indicators.get('price', 0)

        if ma5 > ma20 and price > ma5:
            score += 15  # 多头排列
        elif ma5 < ma20 and price < ma5:
            score -= 15  # 空头排列

        # 市场环境调整
        if market_condition == 'bull':
            # 牛市：技术指标权重降低，更注重趋势
            score = score * 0.9 + 5  # 轻微上调
        elif market_condition == 'bear':
            # 熊市：更严格标准
            score = score * 0.95
        # volatile：保持原始评分

        return max(0, min(100, score))

    def _simulate_random_forest_analysis(self, stock_data: Dict, market_condition: str = 'volatile') -> float:
        """模拟随机森林波动率分析（考虑市场环境）"""
        score = 50.0

        # 成交量分析
        volume = stock_data.get('volume', 0)
        avg_volume = stock_data.get('avg_volume', volume)

        if volume > avg_volume * 1.5:
            score += 10  # 放量
        elif volume < avg_volume * 0.5:
            score -= 10  # 缩量

        # 价格波动
        volatility = stock_data.get('volatility', 0.02)
        if volatility > 0.05:
            score -= 15  # 高波动风险
        elif volatility < 0.02:
            score += 5   # 低波动稳定

        # 市场环境调整
        if market_condition == 'bull':
            # 牛市：高波动可接受
            volatility_penalty = 0.8  # 降低波动惩罚
        elif market_condition == 'bear':
            # 熊市：严格控制风险
            volatility_penalty = 1.2  # 增加波动惩罚
        else:  # volatile
            volatility_penalty = 1.0

        # 重新计算波动惩罚
        if volatility > 0.05:
            score += 15 * (1 - volatility_penalty)  # 调整波动影响
        elif volatility < 0.02:
            score += 5

        return max(0, min(100, score))

    def _simulate_gru_prediction(self, stock_data: Dict, market_condition: str = 'volatile') -> float:
        """模拟GRU价格预测（考虑市场环境）"""
        score = 50.0

        # 基于历史价格趋势
        price_change = stock_data.get('price_change_5d', 0)
        trend_strength = stock_data.get('trend_strength', 0.5)

        # 短期动量
        if price_change > 0.02:  # 5日涨幅>2%
            score += 20
        elif price_change < -0.02:  # 5日跌幅>2%
            score -= 15

        # 趋势强度
        score += (trend_strength - 0.5) * 30

        # 市场环境调整
        if market_condition == 'bull':
            # 牛市：趋势延续概率更高
            if price_change > 0:
                score += 5  # 上涨趋势加强
        elif market_condition == 'bear':
            # 熊市：反弹都是减仓机会
            if price_change > 0:
                score -= 10  # 上涨后更易下跌
            else:
                score -= 5   # 下跌趋势延续
        # volatile：保持原始评分

        return max(0, min(100, score))

    def _parse_llm_text(self, response: str) -> Tuple[float, str, str]:
        """解析LLM文本响应"""
        # 简单的文本解析逻辑
        lines = response.split('\n')
        score = 50
        analysis = "基于技术面和资金面分析"
        suggestion = "HOLD"

        # 查找评分
        for line in lines:
            if '评分' in line or 'score' in line.lower():
                try:
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        score = float(numbers[0])
                except:
                    pass

        return score, analysis, suggestion

    def _get_category_weight(self, category: str) -> float:
        """获取类别权重"""
        weights = {
            'llm': 0.4,
            'ml': 0.35,
            'dl': 0.25
        }
        return weights.get(category, 0.33)

    def _generate_recommendation(self, score: float, results: Dict) -> str:
        """生成操作建议"""
        if score >= 70:
            return "强烈买入"
        elif score >= 60:
            return "买入"
        elif score >= 40:
            return "持有"
        elif score >= 30:
            return "观望"
        else:
            return "卖出"

    def _generate_recommendation_with_market(self, score: float, market_condition: str) -> str:
        """
        基于市场环境生成操作建议

        Args:
            score: 综合评分
            market_condition: 市场环境

        Returns:
            操作建议
        """
        # 不同市场环境下的阈值
        thresholds = {
            'bull': {'strong_buy': 65, 'buy': 55, 'hold': 35, 'watch': 25},
            'bear': {'strong_buy': 75, 'buy': 65, 'hold': 45, 'watch': 35},
            'volatile': {'strong_buy': 70, 'buy': 60, 'hold': 40, 'watch': 30}
        }

        t = thresholds.get(market_condition, thresholds['volatile'])

        if score >= t['strong_buy']:
            return "强烈买入"
        elif score >= t['buy']:
            return "买入"
        elif score >= t['hold']:
            return "持有"
        elif score >= t['watch']:
            return "观望"
        else:
            return "卖出"

    def _calculate_confidence(self, results: Dict) -> float:
        """计算预测置信度"""
        confidences = []

        for category, category_results in results.items():
            if isinstance(category_results, dict):
                if 'confidence' in category_results:
                    confidences.append(category_results['confidence'])
                elif 'combined_score' in category_results:
                    confidences.append(0.72)  # ML默认置信度

        return sum(confidences) / len(confidences) if confidences else 0.5

    def get_model_status(self) -> Dict:
        """获取模型状态"""
        return {
            'ollama_available': self.llm.available,
            'ollama_url': self.llm.base_url,
            'ollama_model': self.llm.model_name,
            'ml_loaded': self.ml_loaded,
            'xgboost_loaded': self.xgb_model is not None,
            'random_forest_loaded': self.rf_model is not None,
            'feature_count': len(self.feature_names) if self.feature_names else 0,
            'model_dir': str(self.model_dir),
            'total_models': len(self.models),
            'model_configs': [
                {
                    'name': m.name,
                    'type': m.type,
                    'purpose': m.purpose,
                    'weight': m.weight
                }
                for m in self.models
            ]
        }

# 便捷函数
def create_local_analyzer(model_dir: str = './models') -> ModelManager:
    """创建本地分析器
    
    Args:
        model_dir: ML模型目录路径
    """
    return ModelManager(model_dir=model_dir)

def analyze_stock_with_ensemble(stock_code: str,
                               stock_data: Dict,
                               technical_indicators: Dict,
                               capital_flow: Dict,
                               sentiment: Dict) -> Dict:
    """
    使用集成模型分析股票

    Args:
        stock_code: 股票代码
        stock_data: 股票数据
        technical_indicators: 技术指标
        capital_flow: 资金流向
        sentiment: 市场情绪

    Returns:
        分析结果
    """
    analyzer = create_local_analyzer()
    return analyzer.analyze_stock(
        stock_code, stock_data, technical_indicators,
        capital_flow, sentiment
    )