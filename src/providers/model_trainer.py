"""
股票预测模型训练器
使用AKShare历史数据训练XGBoost/RandomForest模型
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeatureEngineer:
    """特征工程"""
    
    @staticmethod
    def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_macd(close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD"""
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        return macd, signal, histogram
    
    @staticmethod
    def calculate_kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算KDJ"""
        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low + 1e-10) * 100
        
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return k, d, j
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """计算ADX趋势强度"""
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.abs().rolling(window=period).mean() / atr)
        
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建完整特征集
        
        Args:
            df: 包含 open, high, low, close, volume 的DataFrame
            
        Returns:
            特征DataFrame
        """
        features = pd.DataFrame(index=df.index)
        
        # 基础价格特征
        features['close'] = df['close']
        features['volume'] = df['volume']
        
        # 收益率特征
        features['return_1d'] = df['close'].pct_change(1)
        features['return_5d'] = df['close'].pct_change(5)
        features['return_10d'] = df['close'].pct_change(10)
        
        # 均线特征
        features['ma5'] = df['close'].rolling(5).mean()
        features['ma10'] = df['close'].rolling(10).mean()
        features['ma20'] = df['close'].rolling(20).mean()
        features['ma60'] = df['close'].rolling(60).mean()
        
        # 均线比值
        features['ma5_ma10_ratio'] = features['ma5'] / (features['ma10'] + 1e-10)
        features['ma5_ma20_ratio'] = features['ma5'] / (features['ma20'] + 1e-10)
        features['price_ma5_ratio'] = df['close'] / (features['ma5'] + 1e-10)
        features['price_ma20_ratio'] = df['close'] / (features['ma20'] + 1e-10)
        
        # 成交量特征
        features['volume_ma5'] = df['volume'].rolling(5).mean()
        features['volume_ma10'] = df['volume'].rolling(10).mean()
        features['volume_ratio'] = df['volume'] / (features['volume_ma5'] + 1e-10)
        
        # 波动率
        features['volatility_5d'] = df['close'].pct_change().rolling(5).std()
        features['volatility_10d'] = df['close'].pct_change().rolling(10).std()
        features['volatility_20d'] = df['close'].pct_change().rolling(20).std()
        
        # RSI
        features['rsi_6'] = self.calculate_rsi(df['close'], 6)
        features['rsi_14'] = self.calculate_rsi(df['close'], 14)
        features['rsi_24'] = self.calculate_rsi(df['close'], 24)
        
        # MACD
        macd, signal, histogram = self.calculate_macd(df['close'])
        features['macd'] = macd
        features['macd_signal'] = signal
        features['macd_histogram'] = histogram
        
        # KDJ
        k, d, j = self.calculate_kdj(df['high'], df['low'], df['close'])
        features['kdj_k'] = k
        features['kdj_d'] = d
        features['kdj_j'] = j
        
        # ADX趋势强度
        features['adx'] = self.calculate_adx(df['high'], df['low'], df['close'])
        
        # 布林带
        ma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        features['boll_upper'] = ma20 + 2 * std20
        features['boll_lower'] = ma20 - 2 * std20
        features['boll_width'] = (features['boll_upper'] - features['boll_lower']) / (ma20 + 1e-10)
        features['boll_position'] = (df['close'] - features['boll_lower']) / (features['boll_upper'] - features['boll_lower'] + 1e-10)
        
        # 价格位置
        features['high_low_ratio'] = df['high'] / (df['low'] + 1e-10)
        features['close_open_ratio'] = df['close'] / (df['open'] + 1e-10)
        
        return features


class DataCollector:
    """数据收集器"""
    
    def __init__(self):
        try:
            import akshare as ak
            self.ak = ak
            self.has_akshare = True
        except ImportError:
            self.has_akshare = False
            logger.error("AKShare未安装，请运行: pip install akshare")
    
    def get_stock_list(self, limit: int = 0) -> List[Dict]:
        """获取A股股票列表"""
        if not self.has_akshare:
            return []
        
        try:
            df = self.ak.stock_info_a_code_name()
            stocks = df.to_dict('records')
            
            # 过滤ST股票
            stocks = [s for s in stocks if 'ST' not in s['name'] and '*' not in s['name']]
            
            # 只保留主板
            stocks = [s for s in stocks if s['code'].startswith(('00', '60', '30'))]
            
            if limit > 0:
                stocks = stocks[:limit]
            
            logger.info(f"获取到 {len(stocks)} 只股票")
            return stocks
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    def get_history_data(self, stock_code: str, years: int = 2) -> Optional[pd.DataFrame]:
        """
        获取单只股票历史数据
        
        Args:
            stock_code: 股票代码
            years: 年数
            
        Returns:
            历史数据DataFrame
        """
        if not self.has_akshare:
            return None
        
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y%m%d')
            
            df = self.ak.stock_zh_a_hist(
                symbol=stock_code,
                period='daily',
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'  # 前复权
            )
            
            if df is None or df.empty:
                return None
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # 确保必要列存在
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.warning(f"{stock_code} 缺少必要列")
                return None
            
            return df
            
        except Exception as e:
            logger.debug(f"获取 {stock_code} 历史数据失败: {e}")
            return None


class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, model_dir: str = './models'):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.feature_engineer = FeatureEngineer()
        self.data_collector = DataCollector()
        
        self.xgb_model = None
        self.rf_model = None
        self.feature_names = None
    
    def prepare_training_data(
        self,
        stock_codes: List[str],
        years: int = 2,
        forward_days: int = 5,
        min_return: float = 0.02
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        准备训练数据
        
        Args:
            stock_codes: 股票代码列表
            years: 历史数据年数
            forward_days: 预测未来N天
            min_return: 最小收益率阈值（用于定义涨跌）
            
        Returns:
            特征DataFrame, 标签Series
        """
        all_features = []
        all_labels = []
        
        total = len(stock_codes)
        success_count = 0
        
        for i, code in enumerate(stock_codes):
            if (i + 1) % 50 == 0:
                logger.info(f"处理进度: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
            
            # 获取历史数据
            df = self.data_collector.get_history_data(code, years)
            if df is None or len(df) < 60:
                continue
            
            # 构建特征
            features = self.feature_engineer.build_features(df)
            
            # 构建标签：N日后收益率
            features['future_return'] = df['close'].shift(-forward_days) / df['close'] - 1
            
            # 删除最后N天的数据（没有标签）
            features = features[:-forward_days]
            
            # 删除NaN
            features = features.dropna()
            
            if len(features) < 30:
                continue
            
            # 保存特征名
            if self.feature_names is None:
                self.feature_names = [c for c in features.columns if c != 'future_return']
            
            # 分离特征和标签
            X = features[self.feature_names]
            y = (features['future_return'] > min_return).astype(int)
            
            all_features.append(X)
            all_labels.append(y)
            success_count += 1
        
        logger.info(f"成功处理 {success_count}/{total} 只股票")
        
        if not all_features:
            raise ValueError("没有有效的训练数据")
        
        # 合并所有数据
        X_all = pd.concat(all_features, ignore_index=True)
        y_all = pd.concat(all_labels, ignore_index=True)
        
        logger.info(f"总样本数: {len(X_all)}, 正样本比例: {y_all.mean():.2%}")
        
        return X_all, y_all
    
    def train_xgboost(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2
    ) -> Dict:
        """
        训练XGBoost模型
        
        Returns:
            训练结果字典
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        import xgboost as xgb
        
        logger.info("训练 XGBoost 模型...")
        
        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # 训练模型
        self.xgb_model = xgb.XGBClassifier(
            max_depth=6,
            learning_rate=0.1,
            n_estimators=200,
            objective='binary:logistic',
            eval_metric='auc',
            n_jobs=-1,
            random_state=42
        )
        
        self.xgb_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=50
        )
        
        # 评估
        y_pred = self.xgb_model.predict(X_test)
        y_proba = self.xgb_model.predict_proba(X_test)[:, 1]
        
        results = {
            'model': 'xgboost',
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'auc': roc_auc_score(y_test, y_proba)
        }
        
        logger.info(f"XGBoost 训练结果:")
        logger.info(f"  Accuracy:  {results['accuracy']:.4f}")
        logger.info(f"  Precision: {results['precision']:.4f}")
        logger.info(f"  Recall:    {results['recall']:.4f}")
        logger.info(f"  F1 Score:  {results['f1']:.4f}")
        logger.info(f"  AUC:       {results['auc']:.4f}")
        
        return results
    
    def train_random_forest(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2
    ) -> Dict:
        """
        训练RandomForest模型
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        from sklearn.ensemble import RandomForestClassifier
        
        logger.info("训练 RandomForest 模型...")
        
        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # 训练模型
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=42
        )
        
        self.rf_model.fit(X_train, y_train)
        
        # 评估
        y_pred = self.rf_model.predict(X_test)
        y_proba = self.rf_model.predict_proba(X_test)[:, 1]
        
        results = {
            'model': 'random_forest',
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'auc': roc_auc_score(y_test, y_proba)
        }
        
        logger.info(f"RandomForest 训练结果:")
        logger.info(f"  Accuracy:  {results['accuracy']:.4f}")
        logger.info(f"  Precision: {results['precision']:.4f}")
        logger.info(f"  Recall:    {results['recall']:.4f}")
        logger.info(f"  F1 Score:  {results['f1']:.4f}")
        logger.info(f"  AUC:       {results['auc']:.4f}")
        
        return results
    
    def save_models(self):
        """保存模型"""
        import joblib
        
        # 保存特征名
        feature_path = self.model_dir / 'feature_names.json'
        with open(feature_path, 'w') as f:
            json.dump(self.feature_names, f, indent=2)
        logger.info(f"特征名保存到: {feature_path}")
        
        # 保存XGBoost
        if self.xgb_model is not None:
            xgb_path = self.model_dir / 'xgboost.json'
            self.xgb_model.save_model(str(xgb_path))
            logger.info(f"XGBoost模型保存到: {xgb_path}")
        
        # 保存RandomForest
        if self.rf_model is not None:
            rf_path = self.model_dir / 'random_forest.joblib'
            joblib.dump(self.rf_model, rf_path)
            logger.info(f"RandomForest模型保存到: {rf_path}")
    
    def get_feature_importance(self) -> pd.DataFrame:
        """获取特征重要性"""
        if self.xgb_model is None:
            return None
        
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.xgb_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importance


def main():
    parser = argparse.ArgumentParser(description='股票预测模型训练')
    parser.add_argument('--stocks', type=int, default=100, help='训练股票数量 (0=全部)')
    parser.add_argument('--years', type=int, default=2, help='历史数据年数')
    parser.add_argument('--forward-days', type=int, default=5, help='预测未来N天')
    parser.add_argument('--min-return', type=float, default=0.02, help='最小收益率阈值')
    parser.add_argument('--model-dir', type=str, default='./models', help='模型保存目录')
    
    args = parser.parse_args()
    
    logger.info("="*50)
    logger.info("股票预测模型训练")
    logger.info("="*50)
    logger.info(f"训练股票数: {args.stocks if args.stocks > 0 else '全部'}")
    logger.info(f"历史数据: {args.years}年")
    logger.info(f"预测周期: {args.forward_days}天")
    logger.info(f"最小收益率: {args.min_return*100:.1f}%")
    
    # 初始化训练器
    trainer = ModelTrainer(model_dir=args.model_dir)
    
    # 获取股票列表
    stock_limit = args.stocks if args.stocks > 0 else 0
    stocks = trainer.data_collector.get_stock_list(limit=stock_limit)
    
    if not stocks:
        logger.error("无法获取股票列表")
        return
    
    stock_codes = [s['code'] for s in stocks]
    
    # 准备数据
    logger.info("\n准备训练数据...")
    X, y = trainer.prepare_training_data(
        stock_codes=stock_codes,
        years=args.years,
        forward_days=args.forward_days,
        min_return=args.min_return
    )
    
    # 训练模型
    xgb_results = trainer.train_xgboost(X, y)
    rf_results = trainer.train_random_forest(X, y)
    
    # 显示特征重要性
    importance = trainer.get_feature_importance()
    if importance is not None:
        logger.info("\nTop 10 重要特征:")
        print(importance.head(10).to_string(index=False))
    
    # 保存模型
    trainer.save_models()
    
    # 保存训练报告
    report = {
        'train_date': datetime.now().isoformat(),
        'config': {
            'stocks': args.stocks,
            'years': args.years,
            'forward_days': args.forward_days,
            'min_return': args.min_return
        },
        'xgboost': xgb_results,
        'random_forest': rf_results
    }
    
    report_path = Path(args.model_dir) / 'training_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"\n训练报告保存到: {report_path}")
    logger.info("\n✅ 训练完成!")


if __name__ == '__main__':
    main()