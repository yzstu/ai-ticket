"""
股票选择器配置模块
支持自定义股票列表、代码范围选择等多种选择方式
"""
from typing import List, Dict, Optional, Union
import pandas as pd


class StockSelector:
    """股票选择器 - 支持多种选择策略"""

    def __init__(self, selection_mode: str = "top_n", **kwargs):
        """
        初始化股票选择器

        Args:
            selection_mode: 选择模式
                - "top_n": 按评分取前N只 (默认)
                - "custom": 自定义股票列表
                - "range": 按代码范围选择
                - "all": 所有股票
            **kwargs: 选择参数
                - custom_stocks: 自定义股票代码列表 (selection_mode="custom")
                - code_range: 代码范围 tuple(start, end) (selection_mode="range")
                - max_results: 最大结果数量 (selection_mode="top_n")
        """
        self.selection_mode = selection_mode
        self.custom_stocks = kwargs.get('custom_stocks', [])
        self.code_range = kwargs.get('code_range', None)
        self.max_results = kwargs.get('max_results', 10)

    def filter_stocks(self, stock_list: List[Dict], scored_stocks: List[Dict] = None) -> List[Dict]:
        """
        根据配置过滤股票

        Args:
            stock_list: 原始股票列表
            scored_stocks: 已评分的股票列表 (包含score字段)

        Returns:
            过滤后的股票列表
        """
        if self.selection_mode == "custom":
            return self._filter_custom_stocks(stock_list)
        elif self.selection_mode == "range":
            return self._filter_by_range(stock_list)
        elif self.selection_mode == "all":
            return stock_list
        elif self.selection_mode == "top_n":
            return self._filter_top_n(scored_stocks, stock_list)
        else:
            raise ValueError(f"Unknown selection mode: {self.selection_mode}")

    def _filter_custom_stocks(self, stock_list: List[Dict]) -> List[Dict]:
        """根据自定义股票代码过滤"""
        if not self.custom_stocks:
            print("⚠️ 自定义股票列表为空，返回空结果")
            return []

        custom_set = set(self.custom_stocks)
        filtered = [stock for stock in stock_list if stock['code'] in custom_set]

        print(f"✅ 自定义选择：从 {len(stock_list)} 只股票中筛选出 {len(filtered)} 只指定股票")
        if filtered:
            print(f"   选择的股票：{', '.join([s['code'] for s in filtered[:10]])}")
            if len(filtered) > 10:
                print(f"   ... 等共 {len(filtered)} 只")
        else:
            print(f"   未找到匹配的股票（请检查股票代码格式）")

        return filtered

    def _filter_by_range(self, stock_list: List[Dict]) -> List[Dict]:
        """根据股票代码范围过滤"""
        if not self.code_range:
            print("⚠️ 代码范围未设置，返回空结果")
            return []

        start_code, end_code = self.code_range
        start_code = str(start_code).zfill(6)  # 补齐6位
        end_code = str(end_code).zfill(6)

        filtered = []
        for stock in stock_list:
            code = stock['code']
            if start_code <= code <= end_code:
                filtered.append(stock)

        print(f"✅ 范围选择：代码范围 {start_code}-{end_code}，筛选出 {len(filtered)} 只股票")
        if filtered:
            print(f"   代码范围：{filtered[0]['code']} - {filtered[-1]['code']}")

        return filtered

    def _filter_top_n(self, scored_stocks: List[Dict] = None, stock_list: List[Dict] = None) -> List[Dict]:
        """按评分取前N只"""
        # 如果没有评分数据但有股票列表，返回前N只
        if not scored_stocks and stock_list:
            top_stocks = stock_list[:self.max_results]
            print(f"⚠️ Top-N模式未提供评分数据，返回前 {len(top_stocks)} 只股票（从 {len(stock_list)} 只中筛选）")
            return top_stocks

        if not scored_stocks:
            print("⚠️ 没有评分数据，返回空结果")
            return []

        # 按评分排序
        sorted_stocks = sorted(scored_stocks, key=lambda x: x['score'], reverse=True)

        # 取前N只
        top_stocks = sorted_stocks[:self.max_results]

        print(f"✅ Top-N选择：取前 {len(top_stocks)} 只股票（从 {len(scored_stocks)} 只中筛选）")
        if top_stocks:
            print(f"   最高评分：{top_stocks[0]['score']:.2f}，最低评分：{top_stocks[-1]['score']:.2f}")

        return top_stocks

    def get_config_summary(self) -> Dict:
        """获取当前配置摘要"""
        summary = {
            "selection_mode": self.selection_mode,
            "parameters": {}
        }

        if self.selection_mode == "custom":
            summary["parameters"]["custom_stocks"] = self.custom_stocks
            summary["parameters"]["count"] = len(self.custom_stocks)
        elif self.selection_mode == "range":
            summary["parameters"]["code_range"] = self.code_range
        elif self.selection_mode == "top_n":
            summary["parameters"]["max_results"] = self.max_results
        elif self.selection_mode == "all":
            summary["parameters"]["description"] = "分析所有股票"

        return summary

    @classmethod
    def from_config(cls, config: Dict) -> 'StockSelector':
        """
        从配置字典创建选择器

        Args:
            config: 配置字典，包含：
                - selection_mode: 选择模式
                - 其他模式相关参数

        Returns:
            StockSelector实例
        """
        return cls(**config)

    @classmethod
    def from_file(cls, config_path: str) -> 'StockSelector':
        """
        从配置文件创建选择器

        Args:
            config_path: 配置文件路径（支持JSON/YAML）

        Returns:
            StockSelector实例
        """
        import json
        import yaml

        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)

        return cls.from_config(config)


def create_selector_from_env() -> StockSelector:
    """
    从环境变量创建股票选择器

    环境变量：
    - STOCK_SELECTION_MODE: 选择模式 (top_n/custom/range/all)
    - CUSTOM_STOCKS: 自定义股票代码，逗号分隔
    - CODE_RANGE_START: 代码范围起始
    - CODE_RANGE_END: 代码范围结束
    - MAX_STOCKS: 最大股票数量

    Returns:
        StockSelector实例
    """
    import os

    mode = os.getenv('STOCK_SELECTION_MODE', 'top_n').lower()
    params = {}

    if mode == 'custom':
        stocks_str = os.getenv('CUSTOM_STOCKS', '')
        if stocks_str:
            params['custom_stocks'] = [s.strip() for s in stocks_str.split(',')]
    elif mode == 'range':
        start = os.getenv('CODE_RANGE_START', '')
        end = os.getenv('CODE_RANGE_END', '')
        if start and end:
            params['code_range'] = (start, end)
    elif mode == 'top_n':
        max_stocks = os.getenv('MAX_STOCKS', '10')
        try:
            params['max_results'] = int(max_stocks)
        except ValueError:
            params['max_results'] = 10

    return StockSelector(selection_mode=mode, **params)


# 预设配置示例
PRESET_CONFIGS = {
    "top5": {
        "selection_mode": "top_n",
        "max_results": 5
    },
    "top10": {
        "selection_mode": "top_n",
        "max_results": 10
    },
    "tech_stocks": {
        "selection_mode": "range",
        "code_range": ("000001", "000999")
    },
    "blue_chips": {
        "selection_mode": "range",
        "code_range": ("600000", "600999")
    },
    "custom_list": {
        "selection_mode": "custom",
        "custom_stocks": ["000001", "000002", "600519"]
    }
}